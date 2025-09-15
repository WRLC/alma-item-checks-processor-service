"""SCF item processor service"""

import json
import logging
from typing import Any

import azure.core.exceptions
from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import (
    InstitutionService,
)
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.config import (
    EXCLUDED_NOTES,
    PROVENANCE,
    SCF_NO_ROW_TRAY_STAGE_TABLE,
    SCF_NO_ROW_TRAY_REPORT_TABLE,
    UPDATE_QUEUE,
    NOTIFICATION_QUEUE,
    UPDATED_ITEMS_CONTAINER,
)


class SCFItemProcessor(BaseItemProcessor):
    """SCF item processor service"""

    def should_process(self) -> list[str]:
        """Check if SCF item should be processed

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        should_process: list[str] = []  # initialize empty list of processes

        if not self.shared_checks():  # If doesn't meet basic criteria, stop processiong
            return should_process

        if self.no_x_should_process():  # If barcode doesn't end in X...
            should_process.append("scf_no_x")  # ...flag for processing

        if self.no_row_tray_should_process():  # If missing/wrong row/tray info...
            should_process.append("scf_no_row_tray_data")  # ...flag for processing

        if self.withdrawn_should_process():  # If item marked withdrawn...
            should_process.append("scf_withdrawn_data")  # ...flag for processing

        return should_process

    def process(self, processes: list[str]) -> None:
        """Process SCF item

        Args:
            processes (list[str]): Processes to run
        """
        for process in processes:  # iterate through the flagged processes
            if process == "scf_no_x":  # fix missing X from barcode and notify
                self.no_x_process()
            if (
                process == "scf_no_row_tray_data"
            ):  # stage problem row/tray data for report
                self.no_row_tray_process()
            if process == "scf_withdrawn_data":  # notify to confirm withdrawn item
                self.withdrawn_process()

    def shared_checks(self) -> bool:
        """Check if SCF item doesn't meet conditions for any checks

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.item_data.barcode

        if (  # If in discard temporary location, don't process
            item.holding_data.temp_location.value
            and "disc" in item.holding_data.temp_location.value.lower()
        ):
            logging.info(
                f"Item {barcode} is in a discard temporary location, skipping processing"
            )
            return False

        if (  # If in discard location, don't process
            "disc" in item.item_data.location.value.lower()
        ):
            logging.info(
                f"Item {barcode} is in a discard location, skipping processing"
            )
            return False

        if (  # If not a checked provenance, don't process
            not item.item_data.provenance
            or item.item_data.provenance.desc not in [p["value"] for p in PROVENANCE]
        ):
            logging.info(
                f"Item {barcode} has no checked provenance, skipping processing"
            )
            return False

        return True

    def no_x_should_process(self) -> bool:
        """Check if SCF item ends in X

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode

        if not barcode.endswith("X"):  # check if barcode ends in X
            logging.warning(
                f"ProcessorService.scf_no_x_should_process: barcode {barcode} does not end with X."
            )
            return True

        return False

    def no_x_process(self) -> None:
        """Process SCF item with missing X in barcode"""
        item: Item = self.parsed_item.get("item_data")
        original_barcode: str = item.item_data.barcode
        item.item_data.barcode = original_barcode + "X"  # append X to barcode

        job_id: str = self.generate_job_id("scf_no_x")
        institution_code: str | None = self.parsed_item.get("institution_code")

        if institution_code is None:
            logging.warning(
                "ProcessorService.scf_no_x_process: institution_code was not provided"
            )
            return

        # Get institution ID for queue message
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            institution: Institution | None = (
                institution_service.get_institution_by_code(institution_code)
            )

        if not institution:
            logging.error(
                f"SCFItemProcessor.no_x_process: Institution {institution_code} not found"
            )
            return

        storage_service: StorageService = StorageService()

        # Store updated item data in unified container
        try:
            storage_service.upload_blob_data(
                container_name=UPDATED_ITEMS_CONTAINER,
                blob_name=f"{job_id}.json",
                data=json.dumps(
                    item.__dict__ if hasattr(item, "__dict__") else str(item)
                ).encode(),
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.no_x_process: Failed to upload item data: {e}"
            )
            return

        # Queue item for update service
        update_message: dict[str, Any] = {
            "job_id": job_id,
            "institution_id": institution.id,
            "process_type": "scf_no_x",
        }

        try:
            storage_service.send_queue_message(
                queue_name=UPDATE_QUEUE, message_content=update_message
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.no_x_process: Failed to queue update message: {e}"
            )
            return

    def no_row_tray_should_process(self) -> bool:
        """Check if SCF item has missing or incorrect row/tray data

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")

        if (  # if item has an excluded note, don't process
            item.item_data.internal_note_1.lower().strip()
            in (item.lower().strip() for item in EXCLUDED_NOTES)
        ):
            return False

        if (  # If row/tray data is missing or wrong, process
            self.no_row_tray_data() or self.wrong_row_tray_data("scf")
        ):
            return True

        return False

    def no_row_tray_process(self) -> None:
        """Process SCF item with missing or incorrect row tray data"""
        item: Item = self.parsed_item.get("item_data")  # get item object
        barcode: str = item.item_data.barcode  # get barcode

        if not barcode:  # if no barcode, log error and return
            logging.warning(
                "No barcode found for SCF item with missing or incorrect row tray data"
            )
            return

        entity: dict[str, str] = {  # set entity value
            "PartitionKey": "scf_no_row_tray",  # PartitionKey = subprocess name
            "RowKey": barcode,  # RowKey = barcode
        }

        storage_service: StorageService = StorageService()  # initialize storage service

        storage_service.upsert_entity(  # add barcode to staging table
            table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,  # staging table
            entity=entity,  # barcode entity
        )

    def no_row_tray_report_process(self) -> bool:
        """Process SCF no row tray data by storing updated item and adding to report table"""
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode
        institution_code: str | None = self.parsed_item.get("institution_code")
        job_id = self.generate_job_id("scf_no_row_tray_report")

        if institution_code is None:
            logging.warning(
                "ProcessorService.scf_no_row_tray_report: institution_code was not provided"
            )
            return False

        # Get institution ID for report table
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            institution: Institution | None = (
                institution_service.get_institution_by_code(institution_code)
            )

        if not institution:
            logging.error(
                f"SCFItemProcessor.no_row_tray_report_process: Institution {institution_code} not found"
            )
            return False

        storage_service: StorageService = StorageService()

        # Store item data in unified container
        try:
            storage_service.upload_blob_data(
                container_name=UPDATED_ITEMS_CONTAINER,
                blob_name=f"{job_id}.json",
                data=json.dumps(
                    item.__dict__ if hasattr(item, "__dict__") else str(item)
                ).encode(),
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.no_row_tray_report_process: Failed to upload item data: {e}"
            )
            return False

        # Add to report table for compilation by separate service
        report_entity: dict[str, str] = {
            "PartitionKey": "scf_no_row_tray_report",
            "RowKey": job_id,
            "institution_id": str(institution.id),
            "job_id": job_id,
        }

        try:
            storage_service.upsert_entity(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE, entity=report_entity
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.no_row_tray_report_process: Failed to add to report table: {e}"
            )
            return False

        logging.info(
            f"SCFItemProcessor.no_row_tray_report_process: Successfully processed item {barcode} for reporting"
        )
        return True

    def withdrawn_should_process(self) -> bool:
        """Check if item has withdrawal data

        Returns:
            bool: True if item should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")  # get item object
        barcode: str = item.item_data.barcode  # get barcode
        alt_call_number: str | None = (
            item.item_data.alternative_call_number
        )  # get alt call number
        internal_note_1: str | None = (
            item.item_data.internal_note_1
        )  # get internal note 1

        if (
            alt_call_number == "WD" or internal_note_1 == "WD"
        ):  # if either is "WD," process
            logging.warning(
                f"ProcessorService.scf_withdrawn_should_process: Item {barcode} marked as withdrawn. Processing."
            )
            return True

        return False

    def withdrawn_process(self) -> None:
        """Process SCF item with withdrawal data"""
        item: Item = self.parsed_item.get("item_data")
        job_id: str = self.generate_job_id("scf_withdrawn")
        institution_code: str | None = self.parsed_item.get("institution_code")

        if institution_code is None:
            logging.warning(
                "ProcessorService.scf_withdrawn: institution_code was not provided"
            )
            return

        # Get institution ID for queue message
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            institution: Institution | None = (
                institution_service.get_institution_by_code(institution_code)
            )

        if not institution:
            logging.error(
                f"SCFItemProcessor.withdrawn_process: Institution {institution_code} not found"
            )
            return

        storage_service: StorageService = StorageService()

        # Store withdrawal data in unified container (same format as updated items)
        try:
            storage_service.upload_blob_data(
                container_name=UPDATED_ITEMS_CONTAINER,
                blob_name=f"{job_id}.json",
                data=json.dumps(
                    item.__dict__ if hasattr(item, "__dict__") else str(item)
                ).encode(),
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.withdrawn_process: Failed to upload withdrawal data: {e}"
            )
            return

        # Queue notification for withdrawal (no update needed)
        notification_message: dict[str, Any] = {
            "job_id": job_id,
            "institution_id": institution.id,
            "process_type": "scf_withdrawn",
        }

        try:
            storage_service.send_queue_message(
                queue_name=NOTIFICATION_QUEUE, message_content=notification_message
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"SCFItemProcessor.withdrawn_process: Failed to queue notification: {e}"
            )
