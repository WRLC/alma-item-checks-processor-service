"""Service for processing IZ no row tray reports"""
import logging
from typing import Any

from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.config import IZ_NO_ROW_TRAY_STAGE_TABLE
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import InstitutionService
from alma_item_checks_processor_service.services.iz_item_processor import IZItemProcessor
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.models import Institution


# noinspection PyMethodMayBeStatic
class IZNoRowTrayReportService:
    """Service for processing IZ no row tray staged items and generating reports"""

    def __init__(self) -> None:
        self.storage_service: StorageService = StorageService()

    def process_staged_items_report(self) -> None:
        """Main method to process all staged items and generate report"""
        logging.info("Starting IZ no row tray report processing")

        # Get staged items
        staged_entities: list[dict[str, Any]] = self._get_staged_items()
        if not staged_entities:
            logging.info("No staged items found for processing")
            return

        # Process each staged item
        processed_count, failed_count = self._process_staged_items(staged_entities)

        # Clear staging table after processing
        self._clear_staging_table(staged_entities)

        logging.info(
            f"IZ no row tray report processing completed. Processed: {processed_count}, "
            f"Failed: {failed_count}"
        )

    def _get_staged_items(self) -> list[dict[str, Any]]:
        """Retrieve all staged items from staging table"""
        try:
            staged_entities: list[dict[str, Any]] | None = self.storage_service.get_entities(
                table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                filter_query="PartitionKey eq 'iz_no_row_tray'"
            )
            return staged_entities or []
        except Exception as e:
            logging.error(f"Failed to query staged items: {e}")
            return []

    def _process_staged_items(self, staged_entities: list[dict[str, Any]]) -> tuple[int, int]:
        """Process each staged item and return processed and failed counts"""
        processed_count: int = 0
        failed_count: int = 0

        for entity in staged_entities:
            barcode: str | None = entity.get('RowKey')
            institution_code: str | None = entity.get('institution_code')

            if not barcode or not institution_code:
                failed_count += 1
                continue

            logging.info(f"Processing staged item: {barcode} from institution {institution_code}")

            # Process individual item
            result: dict[str, Any] = self._process_single_item(barcode, institution_code)
            if result['success']:
                processed_count += 1
                logging.info(f"Successfully processed item {barcode}")
            else:
                failed_count += 1
                logging.warning(f"Failed to process item {barcode}: {result['reason']}")

        return processed_count, failed_count

    def _process_single_item(self, barcode: str, institution_code: str) -> dict[str, Any]:
        """Process a single staged item"""
        # Get institution
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            institution: Institution | None = institution_service.get_institution_by_code(institution_code)

        if not institution:
            return {
                'success': False,
                'reason': f'Institution {institution_code} not found in database'
            }

        # Re-retrieve item from Alma
        item: Item | None = BaseItemProcessor.retrieve_item_by_barcode(institution, barcode)
        if not item:
            return {
                'success': False,
                'reason': 'Item not found in Alma'
            }

        # Create parsed_item structure for processor
        parsed_item: dict[str, Any] = {
            "institution_code": institution_code,
            "item_data": item
        }

        # Check if item should still be processed
        processor: IZItemProcessor = IZItemProcessor(parsed_item)
        if not processor.no_row_tray_should_process():
            return {
                'success': False,
                'reason': 'No longer meets processing criteria'
            }

        # Process item - this updates the item with SCF data, stores in container, and queues for update
        updated: bool = processor.no_row_tray_report_process()
        if updated:
            return {'success': True}
        else:
            return {
                'success': False,
                'reason': 'Failed to update item with SCF data'
            }

    def _clear_staging_table(self, staged_entities: list[dict[str, Any]]) -> None:
        """Clear all staged entities from the staging table in batches"""
        logging.info(f"Clearing {len(staged_entities)} items from staging table")

        # Process in batches of 100 (Azure Table Storage batch limit)
        batch_size: int = 100
        total_deleted: int = 0

        for i in range(0, len(staged_entities), batch_size):
            batch: list[dict[str, Any]] = staged_entities[i:i + batch_size]
            batch_deleted: int = 0

            for entity in batch:
                barcode: str | None = entity.get('RowKey')
                if not barcode:
                    continue

                try:
                    self.storage_service.delete_entity(
                        table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                        partition_key="iz_no_row_tray",
                        row_key=barcode
                    )
                    batch_deleted += 1
                except Exception as e:
                    logging.warning(f"Failed to remove staged item {barcode}: {e}")

            total_deleted += batch_deleted
            logging.info(f"Deleted batch {i//batch_size + 1}: {batch_deleted}/{len(batch)} items")

        logging.info(f"Successfully deleted {total_deleted}/{len(staged_entities)} staged items")
