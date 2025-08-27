"""Service for processing SCF no row tray reports"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from wrlc_alma_api_client.models import Item
from wrlc_azure_storage_service import StorageService

from alma_item_checks_processor_service.config import (
    SCF_NO_ROW_TRAY_STAGE_TABLE,
    REPORTS_CONTAINER,
    NOTIFICATION_QUEUE
)
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import InstitutionService
from alma_item_checks_processor_service.services.scf_item_processor import SCFItemProcessor
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.models import Institution


# noinspection PyMethodMayBeStatic
class SCFNoRowTrayReportService:
    """Service for processing SCF no row tray staged items and generating reports"""
    
    def __init__(self) -> None:
        self.storage_service: StorageService = StorageService()
        self.scf_institution: Institution | None = None
        
    def process_staged_items_report(self) -> None:
        """Main method to process all staged items and generate report"""
        logging.info("Starting SCF no row tray report processing")
        
        # Get SCF institution
        self.scf_institution = self._get_scf_institution()
        if not self.scf_institution:
            logging.error("SCF institution not found in database")
            return
            
        # Get staged items
        staged_entities: list[dict[str, Any]] = self._get_staged_items()
        if not staged_entities:
            logging.info("No staged items found for processing")
            return
            
        # Process each staged item
        processed_items, failed_items = self._process_staged_items(staged_entities)
        
        # Clear staging table after processing
        self._clear_staging_table(staged_entities)
        
        # Generate and store report
        report_blob_name: str | None = self._generate_report(
            len(staged_entities), processed_items, failed_items
        )
        
        if report_blob_name:
            # Send notification
            self._send_notification(report_blob_name)
            
        logging.info(
            f"SCF no row tray report processing completed. Processed: {len(processed_items)}, "
            f"Failed: {len(failed_items)}"
        )
    
    def _get_scf_institution(self) -> Institution | None:
        """Get SCF institution from database"""
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            return institution_service.get_institution_by_code("scf")
    
    def _get_staged_items(self) -> list[dict[str, Any]]:
        """Retrieve all staged items from staging table"""
        try:
            staged_entities: list[dict[str, Any]] | None = self.storage_service.get_entities(
                table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,
                filter_query="PartitionKey eq 'scf_no_row_tray'"
            )
            return staged_entities or []
        except Exception as e:
            logging.error(f"Failed to query staged items: {e}")
            return []
    
    def _process_staged_items(self, staged_entities: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        """Process each staged item and return processed and failed lists"""
        processed_items: list[dict] = []
        failed_items: list[dict] = []
        
        for entity in staged_entities:
            barcode: str | None = entity.get('RowKey')
            if not barcode:
                continue
                
            logging.info(f"Processing staged item: {barcode}")
            
            # Process individual item
            result: dict[str, Any] = self._process_single_item(barcode)
            if result['success']:
                processed_items.append({
                    "barcode": barcode,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
                logging.info(f"Successfully processed item {barcode}")
            else:
                failed_items.append({
                    "barcode": barcode,
                    "reason": result['reason']
                })
                logging.warning(f"Failed to process item {barcode}: {result['reason']}")
                
        return processed_items, failed_items
    
    def _process_single_item(self, barcode: str) -> dict[str, Any]:
        """Process a single staged item"""
        # Re-retrieve item from Alma
        item: Item | None = BaseItemProcessor.retrieve_item_by_barcode(self.scf_institution, barcode)
        if not item:
            return {
                'success': False, 
                'reason': 'Item not found in Alma'
            }

        # Create parsed_item structure for processor
        parsed_item: dict[str, Any] = {
            "institution_code": "scf",
            "item_data": item
        }

        # Check if item should still be processed
        processor: SCFItemProcessor = SCFItemProcessor(parsed_item)
        if not processor.no_row_tray_should_process():
            return {
                'success': False,
                'reason': 'No longer meets processing criteria'
            }

        # Process item for reporting
        success: bool = processor.no_row_tray_report_process()
        if success:
            return {'success': True}
        else:
            return {
                'success': False,
                'reason': 'Processing failed'
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
                        table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,
                        partition_key="scf_no_row_tray",
                        row_key=barcode
                    )
                    batch_deleted += 1
                except Exception as e:
                    logging.warning(f"Failed to remove staged item {barcode}: {e}")
            
            total_deleted += batch_deleted
            logging.info(f"Deleted batch {i//batch_size + 1}: {batch_deleted}/{len(batch)} items")
        
        logging.info(f"Successfully deleted {total_deleted}/{len(staged_entities)} staged items")
    
    def _generate_report(
            self, total_staged: int, processed_items: list[dict], failed_items: list[dict]
    ) -> str | None:
        """Generate JSON report and store in container"""
        report: dict[str, Any] = {
            "report_type": "scf_no_row_tray",
            "institution_id": self.scf_institution.id,
            "institution_code": "scf",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_staged": total_staged,
                "successfully_processed": len(processed_items),
                "failed": len(failed_items)
            },
            "processed_items": processed_items,
            "failed_items": failed_items
        }

        # Store report in container
        report_id: str = f"scf_no_row_tray_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        try:
            self.storage_service.upload_blob_data(
                container_name=REPORTS_CONTAINER,
                blob_name=report_id + ".json",
                data=json.dumps(report, indent=2).encode()
            )
            logging.info(f"Report stored as {report_id}.json")
            return report_id
        except Exception as e:
            logging.error(f"Failed to store report: {e}")
            return None
    
    def _send_notification(self, report_id: str) -> None:
        """Send notification message about completed report"""
        notification_message: dict[str, Any] = {
            "report_id": report_id,
            "institution_id": self.scf_institution.id,
            "process_type": "scf_no_row_tray_report"
        }

        try:
            self.storage_service.send_queue_message(
                queue_name=NOTIFICATION_QUEUE,
                message_content=notification_message
            )
            logging.info("Report notification sent")
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")
