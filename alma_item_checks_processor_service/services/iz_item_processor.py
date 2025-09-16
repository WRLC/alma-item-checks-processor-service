"""IZ item processor service"""

import json
import logging
import re

import azure.core.exceptions
from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.config import (
    CHECKED_IZ_LOCATIONS,
    IZ_NO_ROW_TRAY_STAGE_TABLE,
    UPDATE_QUEUE,
    UPDATED_ITEMS_CONTAINER,
    STORAGE_CONNECTION_STRING,
)
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import (
    InstitutionService,
)
from alma_item_checks_processor_service.models import Institution


# noinspection PyMethodMayBeStatic
class IZItemProcessor(BaseItemProcessor):
    """IZ item processor service"""

    def should_process(self) -> list[str] | None:
        """Check if IZ item should be processed"""
        should_process: list[str] = []

        if self.no_row_tray_should_process():
            should_process.append("iz_no_row_tray")

        return should_process

    def process(self, processes: list[str]) -> None:
        """Process IZ item

        Args:
            processes (list[str]): Processes to run
        """
        for process in processes:
            if process == "iz_no_row_tray":
                self.no_row_tray_process()

    def no_row_tray_should_process(self) -> bool:
        """Check if IZ no row tray data"""
        item: Item = self.parsed_item.get("item_data")
        iz: str | None = self.parsed_item.get("institution_code")
        location_code: str | None = item.item_data.location.value
        temp_location_code: str | None = item.holding_data.temp_location.value

        if iz is None:
            return False

        if (
            location_code not in CHECKED_IZ_LOCATIONS
            and temp_location_code not in CHECKED_IZ_LOCATIONS
        ):
            return False

        if self.no_row_tray_data() or self.wrong_row_tray_data(iz):
            return True

        return False

    def no_row_tray_process(self) -> None:
        """Stage IZ item with missing or incorrect row tray data"""
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode
        institution_code: str | None = self.parsed_item.get("institution_code")

        if institution_code is None:
            logging.warning("No institution code found")
            return

        if not barcode:
            logging.warning(
                "No barcode found for IZ item with missing or incorrect row tray data"
            )
            return

        entity: dict[str, str] = {
            "PartitionKey": "iz_no_row_tray",
            "RowKey": barcode,
            "institution_code": institution_code,
        }

        storage_service: StorageService = StorageService(
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

        storage_service.upsert_entity(
            table_name=IZ_NO_ROW_TRAY_STAGE_TABLE, entity=entity
        )

    def no_row_tray_report_process(self) -> bool:
        """Process IZ no row tray data by looking up SCF item and updating IZ item"""
        item: Item = self.parsed_item.get("item_data")
        original_barcode: str = item.item_data.barcode

        # Step 1: Add X to barcode
        scf_barcode = original_barcode + "X"
        logging.info(
            f"IZItemProcessor.no_row_tray_report_process: Looking for SCF item with barcode {scf_barcode}"
        )

        # Step 2: Retrieve SCF item by modified barcode
        scf_item = self._get_scf_item_by_barcode(scf_barcode)
        if not scf_item:
            logging.warning(
                f"IZItemProcessor.no_row_tray_report_process: SCF item not found for barcode {scf_barcode}"
            )
            return False

        # Step 3: Check if SCF item has correct row/tray data
        if not self._scf_item_has_correct_row_tray_data(scf_item):
            logging.info(
                f"IZItemProcessor.no_row_tray_report_process: SCF item {scf_barcode} does "
                "not have correct row/tray data"
            )
            return False

        # Step 4: Update IZ item with SCF data
        updated = self._update_iz_item_with_scf_data(item, scf_item)
        if updated:
            logging.info(
                f"IZItemProcessor.no_row_tray_report_process: Successfully updated IZ item {original_barcode} "
                "with SCF row/tray data"
            )

            # Step 5: Store updated item data and queue for downstream processing
            self._handle_successful_update(item, "iz_no_row_tray")
            return True
        else:
            logging.warning(
                f"IZItemProcessor.no_row_tray_report_process: Failed to update IZ item {original_barcode}"
            )
            return False

    def _get_scf_item_by_barcode(self, barcode: str) -> Item | None:
        """Retrieve SCF item by barcode"""
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)

            # Try 'scf' first
            scf_institution: Institution | None = (
                institution_service.get_institution_by_code("scf")
            )

            # Fall back to 'scf-psb' for debugging
            if scf_institution is None:
                logging.info(
                    "SCF institution not found, falling back to scf-psb for debugging"
                )
                scf_institution = institution_service.get_institution_by_code("scf-psb")

        if not scf_institution:
            logging.error(
                "IZItemProcessor._get_scf_item_by_barcode: Neither SCF nor scf-psb institution found in database"
            )
            return None

        return BaseItemProcessor.retrieve_item_by_barcode(scf_institution, barcode)

    def _scf_item_has_correct_row_tray_data(self, scf_item: Item) -> bool:
        """Check if SCF item has correct row/tray data in alt call number or internal note 1"""

        pattern = r"^R.*M.*S"
        fields_to_check = [
            scf_item.item_data.alternative_call_number,
            scf_item.item_data.internal_note_1,
        ]

        for field_value in fields_to_check:
            if field_value and field_value.strip():
                if re.search(pattern=pattern, string=field_value):
                    logging.info(
                        "IZItemProcessor._scf_item_has_correct_row_tray_data: Found correct format in field: "
                        f"{field_value}"
                    )
                    return True

        return False

    def _update_iz_item_with_scf_data(self, iz_item: Item, scf_item: Item) -> bool:
        """Update IZ item's alt call number and internal note 1 with SCF data"""
        try:
            # Update alt call number if SCF has valid data
            if (
                scf_item.item_data.alternative_call_number
                and scf_item.item_data.alternative_call_number.strip()
            ):
                iz_item.item_data.alternative_call_number = (
                    scf_item.item_data.alternative_call_number
                )
                logging.info(
                    f"Updated alt call number: {scf_item.item_data.alternative_call_number}"
                )

            # Update internal note 1 if SCF has valid data
            if (
                scf_item.item_data.internal_note_1
                and scf_item.item_data.internal_note_1.strip()
            ):
                iz_item.item_data.internal_note_1 = scf_item.item_data.internal_note_1
                logging.info(
                    f"Updated internal note 1: {scf_item.item_data.internal_note_1}"
                )

            return True
        except Exception as e:
            logging.error(
                f"IZItemProcessor._update_iz_item_with_scf_data: Error updating item: {e}"
            )
            return False

    def _handle_successful_update(self, item: Item, process_type: str) -> None:
        """Handle successful item update by storing data and adding to report table"""
        institution_code = self.parsed_item.get("institution_code")
        job_id = self.generate_job_id(process_type)

        if institution_code is None:
            logging.error(
                "IZItemProcessor._handle_successful_update: No institution code found"
            )
            return

        storage_service = StorageService(
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

        # Store updated item data in unified container
        try:
            storage_service.upload_blob_data(
                container_name=UPDATED_ITEMS_CONTAINER,
                blob_name=f"{job_id}.json",
                data=json.dumps(
                    item.model_dump()
                    if hasattr(item, "model_dump")
                    else (item.__dict__ if hasattr(item, "__dict__") else str(item)),
                    default=str,
                ).encode(),
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"IZItemProcessor._handle_successful_update: Failed to upload item data: {e}"
            )
            return

        # Get institution ID for update queue message
        with SessionMaker() as db:
            institution_service = InstitutionService(db)
            institution = institution_service.get_institution_by_code(institution_code)

        if not institution:
            logging.error(
                f"IZItemProcessor._handle_successful_update: Institution {institution_code} not found"
            )
            return

        # Queue item for update service
        update_message = {
            "job_id": job_id,
            "institution_id": institution.id,
            "process_type": process_type,
        }

        try:
            storage_service.send_queue_message(
                queue_name=UPDATE_QUEUE, message_content=update_message
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError) as e:
            logging.error(
                f"IZItemProcessor._handle_successful_update: Failed to queue update message: {e}"
            )
