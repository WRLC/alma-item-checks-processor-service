"""SCF item processor service"""
import json
import logging

import azure.core.exceptions
from wrlc_alma_api_client.models import Item

from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from wrlc_azure_storage_service import StorageService

from alma_item_checks_processor_service.config import (
    EXCLUDED_NOTES,
    PROVENANCE,
    SCF_NO_ROW_TRAY_STAGE_TABLE,
    SCF_NO_X_CONTAINER,
    SCF_NO_X_QUEUE,
    SCF_WD_CONTAINER,
    SCF_WD_QUEUE,
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
            should_process.append('scf_no_x')  # ...flag for processing

        if self.no_row_tray_should_process():  # If missing/wrong row/tray info...
            should_process.append('scf_no_row_tray_data')  # ...flag for processing

        if self.withdrawn_should_process():  # If item marked withdrawn...
            should_process.append('scf_withdrawn_data')   # ...flag for processing

        return should_process

    def process(self, processes: list[str]) -> None:
        """Process SCF item

        Args:
            processes (list[str]): Processes to run
        """
        for process in processes:  # iterate through the flagged processes
            if process == "scf_no_x":  # fix missing X from barcode and notify
                self.no_x_process()
            if process == "scf_no_row_tray_data":  # stage problem row/tray data for report
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
            item.holding_data.temp_location.value and
            'disc' in item.holding_data.temp_location.value.lower()
        ):
            logging.info(f"Item {barcode} is in a discard temporary location, skipping processing")
            return False

        if (  # If in discard location, don't process
            'disc' in item.item_data.location.value.lower()
        ):
            logging.info(f"Item {barcode} is in a discard location, skipping processing")
            return False

        if (  # If not a checked provenance, don't process
            not item.item_data.provenance or item.item_data.provenance.desc not in [p['value'] for p in PROVENANCE]
        ):
            logging.info(f"Item {barcode} has no checked provenance, skipping processing")
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
            logging.warning(f"ProcessorService.scf_no_x_should_process: barcode {barcode} does not end with X.")
            return True

        return False

    def no_x_process(self) -> None:
        """Process SCF item with missing X in barcode
        """
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode  # get barcode value
        item.item_data.barcode = barcode + "X"  # append X to barcode

        job_id = self.generate_job_id("scf_no_x")

        storage_service: StorageService = StorageService()  # initialize storage service

        try:
            storage_service.upload_blob_data(  # upload item data dict blob
                container_name=SCF_NO_X_CONTAINER,  # container
                blob_name=job_id + ".json",  # blob name
                data=json.dumps(item).encode()  # data
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return

        try:
            storage_service.send_queue_message(  # send claim ticket
                queue_name=SCF_NO_X_QUEUE,  # queue
                message_content={"job_id": job_id}  # message
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return

    def no_row_tray_should_process(self) -> bool:
        """Check if SCF item has missing or incorrect row/tray data

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")

        if (  # if item has an excluded note, don't process
            item.item_data.internal_note_1.lower().strip() in (item.lower().strip() for item in EXCLUDED_NOTES)
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
            logging.warning("No barcode found for SCF item with missing or incorrect row tray data")
            return

        entity: dict[str, str] = {  # set entity value
            "PartitionKey": "scf_no_row_tray",  # PartitionKey = subprocess name
            "RowKey": barcode  # RowKey = barcode
        }

        storage_service: StorageService = StorageService()  # initialize storage service

        storage_service.upsert_entity(  # add barcode to staging table
            table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,  # staging table
            entity=entity  # barcode entity
        )

    def withdrawn_should_process(self) -> bool:
        """Check if item has withdrawal data

        Returns:
            bool: True if item should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")  # get item object
        barcode: str = item.item_data.barcode  # get barcode
        alt_call_number: str | None = item.item_data.alternative_call_number  # get alt call number
        internal_note_1: str | None = item.item_data.internal_note_1  # get internal note 1

        if alt_call_number == "WD" or internal_note_1 == "WD":  # if either is "WD," process
            logging.warning(
                f"ProcessorService.scf_withdrawn_should_process: Item {barcode} marked as withdrawn. Processing."
            )
            return True

        return False

    def withdrawn_process(self) -> None:
        """Process SCF item with withdrawal data"""
        item: Item = self.parsed_item.get("item_data")
        job_id = self.generate_job_id("scf_withdrawn")

        storage_service: StorageService = StorageService()

        try:
            storage_service.upload_blob_data(
                container_name=SCF_WD_CONTAINER,
                blob_name=job_id + ".json",
                data=json.dumps(item).encode()
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return

        try:
            storage_service.send_queue_message(
                queue_name=SCF_WD_QUEUE,
                message_content={"job_id": job_id}
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return
