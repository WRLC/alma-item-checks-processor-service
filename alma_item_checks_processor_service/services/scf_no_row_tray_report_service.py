"""Service for processing SCF no row tray reports"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.config import (
    SCF_INSTITUTION_CODE,
    SCF_NO_ROW_TRAY_STAGE_TABLE,
    SCF_NO_ROW_TRAY_REPORT_TABLE,
    SCF_NO_ROW_TRAY_BATCH_QUEUE,
    SCF_NO_ROW_TRAY_BATCH_SIZE,
    REPORTS_CONTAINER,
    NOTIFICATION_QUEUE,
    STORAGE_CONNECTION_STRING,
)
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import (
    InstitutionService,
)
from alma_item_checks_processor_service.services.scf_item_processor import (
    SCFItemProcessor,
)
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.models import Institution


# noinspection PyMethodMayBeStatic
class SCFNoRowTrayReportService:
    """Service for processing SCF no row tray staged items and generating reports"""

    def __init__(self) -> None:
        self.storage_service: StorageService = StorageService(
            storage_connection_string=STORAGE_CONNECTION_STRING
        )
        self.scf_institution: Institution | None = None

    def process_staged_items_report(self) -> None:
        """Main method to initiate batch processing of staged items"""
        logging.info("Starting SCF no row tray report batch processing")

        # Check if a job is already running
        if self._is_job_already_running():
            logging.info("Batch job already in progress, skipping this execution")
            return

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

        # Create batch job and split into smaller batches for processing
        job_id = self._create_batch_job(len(staged_entities))
        self._enqueue_batches(staged_entities, job_id)

        logging.info(
            f"SCF no row tray batch processing initiated. Job ID: {job_id}, "
            f"Total items: {len(staged_entities)}, "
            f"Batches: {(len(staged_entities) + SCF_NO_ROW_TRAY_BATCH_SIZE - 1) // SCF_NO_ROW_TRAY_BATCH_SIZE}"
        )

    def _get_scf_institution(self) -> Institution | None:
        """Get SCF institution from database"""
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)

            institution = institution_service.get_institution_by_code(
                SCF_INSTITUTION_CODE
            )
            if institution:
                return institution
        return None

    def _get_staged_items(self) -> list[dict[str, Any]]:
        """Retrieve all staged items from staging table"""
        try:
            staged_entities: list[dict[str, Any]] | None = (
                self.storage_service.get_entities(
                    table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,
                    filter_query="PartitionKey eq 'scf_no_row_tray'",
                )
            )
            return staged_entities or []
        except Exception as e:
            logging.error(f"Failed to query staged items: {e}")
            return []

    def _process_single_item(self, barcode: str) -> dict[str, Any]:
        """Process a single staged item"""
        if not self.scf_institution:
            logging.error("SCF institution not found in database")
            return {}

        # Re-retrieve item from Alma
        item: Item | None = BaseItemProcessor.retrieve_item_by_barcode(
            self.scf_institution, barcode
        )  # type: ignore
        if not item:
            return {"success": False, "reason": "Item not found in Alma"}

        # Create parsed_item structure for processor
        parsed_item: dict[str, Any] = {
            "institution_code": self.scf_institution.code,
            "item_data": item,
        }

        # Check if item should still be processed
        processor: SCFItemProcessor = SCFItemProcessor(parsed_item)
        if not processor.no_row_tray_should_process():
            return {"success": False, "reason": "No longer meets processing criteria"}

        return {"success": True}

    def _is_job_already_running(self) -> bool:
        """Check if there's already a batch job in progress"""
        try:
            job_entities = self.storage_service.get_entities(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE,
                filter_query="PartitionKey eq 'batch_job' and status eq 'in_progress'",
            )

            if job_entities and len(job_entities) > 0:
                logging.info(f"Found {len(job_entities)} jobs already in progress")
                return True

            return False
        except Exception as e:
            logging.error(f"Failed to check for existing jobs: {e}")
            # If we can't check, assume no job is running to avoid blocking
            return False

    def _create_batch_job(self, total_items: int) -> str:
        """Create a batch job record in the report table"""
        job_id = str(uuid.uuid4())
        total_batches = (
            total_items + SCF_NO_ROW_TRAY_BATCH_SIZE - 1
        ) // SCF_NO_ROW_TRAY_BATCH_SIZE

        job_record = {
            "PartitionKey": "batch_job",
            "RowKey": job_id,
            "status": "in_progress",
            "total_items": total_items,
            "total_batches": total_batches,
            "completed_batches": 0,
            "processed_items": 0,
            "failed_items": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "institution_code": "scf",
        }

        try:
            self.storage_service.upsert_entity(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE, entity=job_record
            )
            logging.info(
                f"Created batch job {job_id} for {total_items} items in {total_batches} batches"
            )
        except Exception as e:
            logging.error(f"Failed to create batch job record: {e}")
            raise

        return job_id

    def _enqueue_batches(
        self, staged_entities: list[dict[str, Any]], job_id: str
    ) -> None:
        """Split staged items into batches and enqueue for processing"""
        for i in range(0, len(staged_entities), SCF_NO_ROW_TRAY_BATCH_SIZE):
            batch = staged_entities[i : i + SCF_NO_ROW_TRAY_BATCH_SIZE]
            batch_number = (i // SCF_NO_ROW_TRAY_BATCH_SIZE) + 1

            # Extract barcodes from entities
            barcodes = [
                entity.get("RowKey") for entity in batch if entity.get("RowKey")
            ]

            batch_message = {
                "job_id": job_id,
                "batch_number": batch_number,
                "barcodes": barcodes,
            }

            try:
                self.storage_service.send_queue_message(
                    queue_name=SCF_NO_ROW_TRAY_BATCH_QUEUE,
                    message_content=batch_message,
                )
                logging.info(
                    f"Enqueued batch {batch_number} with {len(barcodes)} items"
                )
            except Exception as e:
                logging.error(f"Failed to enqueue batch {batch_number}: {e}")
                # Continue with other batches even if one fails

    def process_batch(
        self, job_id: str, batch_number: int, barcodes: list[str]
    ) -> None:
        """Process a single batch of items"""
        logging.info(
            f"Processing batch {batch_number} for job {job_id} with {len(barcodes)} items"
        )

        # Get SCF institution
        self.scf_institution = self._get_scf_institution()
        if not self.scf_institution:
            logging.error("SCF institution not found in database")
            return

        # Process items in this batch
        processed_items = []
        failed_items = []

        for barcode in barcodes:
            logging.info(f"Processing item: {barcode}")
            result = self._process_single_item(barcode)

            if result["success"]:
                # Store item with missing/incorrect row tray data in report table
                item_record = {
                    "PartitionKey": "scf_no_row_tray_item",
                    "RowKey": f"{job_id}_{barcode}",
                    "job_id": job_id,
                    "barcode": barcode,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "institution_code": "scf",
                }

                try:
                    self.storage_service.upsert_entity(
                        table_name=SCF_NO_ROW_TRAY_REPORT_TABLE, entity=item_record
                    )
                except Exception as e:
                    logging.warning(f"Failed to store report item {barcode}: {e}")

                processed_items.append(
                    {
                        "barcode": barcode,
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                logging.info(
                    f"Item {barcode} added to report (has missing/incorrect row tray data)"
                )
            else:
                # Item doesn't meet criteria or couldn't be retrieved - not included in report
                failed_items.append({"barcode": barcode, "reason": result["reason"]})
                logging.info(
                    f"Item {barcode} not included in report: {result['reason']}"
                )

        # Update batch job progress
        self._update_batch_progress(job_id, len(processed_items), len(failed_items))

        # Clear processed items from staging table
        self._clear_batch_from_staging(barcodes)

        logging.info(
            f"Completed batch {batch_number}: {len(processed_items)} processed, {len(failed_items)} failed"
        )

    def _update_batch_progress(
        self, job_id: str, batch_processed: int, batch_failed: int
    ) -> None:
        """Update batch job progress and check if complete"""
        try:
            # Get current job record
            job_entities = self.storage_service.get_entities(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE,
                filter_query=f"PartitionKey eq 'batch_job' and RowKey eq '{job_id}'",
            )

            if not job_entities or len(job_entities) == 0:
                logging.error(f"Batch job {job_id} not found")
                return

            job_entity = job_entities[0]

            # Update counters
            new_completed_batches = job_entity["completed_batches"] + 1
            new_processed_items = job_entity["processed_items"] + batch_processed
            new_failed_items = job_entity["failed_items"] + batch_failed

            # Update entity
            job_entity["completed_batches"] = new_completed_batches
            job_entity["processed_items"] = new_processed_items
            job_entity["failed_items"] = new_failed_items

            # Check if job is complete
            if new_completed_batches >= job_entity["total_batches"]:
                job_entity["status"] = "completed"
                job_entity["completed_at"] = datetime.now(timezone.utc).isoformat()

            self.storage_service.upsert_entity(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE, entity=job_entity
            )

            # If job is complete, generate final report
            if job_entity["status"] == "completed":
                self._generate_final_report(job_entity)

        except Exception as e:
            logging.error(f"Failed to update batch progress for job {job_id}: {e}")

    def _generate_final_report(self, job_entity: dict[str, Any]) -> None:
        """Generate final report when all batches are complete"""
        job_id = job_entity["RowKey"]
        logging.info(f"Generating final report for job {job_id}")

        # Get processed items from report table
        processed_items = self._get_processed_items_for_job(job_id, "processed_item")
        failed_items = self._get_processed_items_for_job(job_id, "failed_item")

        report = {
            "report_type": "scf_no_row_tray",
            "institution_id": self.scf_institution.id if self.scf_institution else None,
            "institution_code": "scf",
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processing_started_at": job_entity["created_at"],
            "processing_completed_at": job_entity["completed_at"],
            "summary": {
                "total_items": job_entity["total_items"],
                "total_batches": job_entity["total_batches"],
                "successfully_processed": len(processed_items),
                "failed": len(failed_items),
            },
            "processed_items": processed_items,
            "failed_items": failed_items,
        }

        # Store report in container
        report_name = f"scf_no_row_tray_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        try:
            self.storage_service.upload_blob_data(
                container_name=REPORTS_CONTAINER,
                blob_name=report_name + ".json",
                data=json.dumps(report, indent=2).encode(),
            )
            logging.info(f"Final report stored as {report_name}.json")

            # Send notification
            self._send_notification(report_name)

        except Exception as e:
            logging.error(f"Failed to store final report: {e}")

    def _get_processed_items_for_job(
        self, job_id: str, partition_key: str
    ) -> list[dict[str, Any]]:
        """Get processed or failed items for a specific job from the report table"""
        try:
            item_entities = self.storage_service.get_entities(
                table_name=SCF_NO_ROW_TRAY_REPORT_TABLE,
                filter_query=f"PartitionKey eq '{partition_key}' and job_id eq '{job_id}'",
            )

            items = []
            for entity in item_entities or []:
                item_data = {
                    "barcode": entity.get("barcode"),
                    "processed_at": entity.get("processed_at"),
                }
                if partition_key == "failed_item":
                    item_data["reason"] = entity.get("reason")
                items.append(item_data)

            return items

        except Exception as e:
            logging.error(f"Failed to get {partition_key} items for job {job_id}: {e}")
            return []

    def _clear_batch_from_staging(self, barcodes: list[str]) -> None:
        """Clear specific barcodes from staging table"""
        for barcode in barcodes:
            try:
                self.storage_service.delete_entity(
                    table_name=SCF_NO_ROW_TRAY_STAGE_TABLE,
                    partition_key="scf_no_row_tray",
                    row_key=barcode,
                )
            except Exception as e:
                logging.warning(f"Failed to remove staged item {barcode}: {e}")

    def _send_notification(self, job_id: str) -> None:
        """Send notification message about completed report"""
        if self.scf_institution is not None:
            notification_message: dict[str, Any] = {
                "job_id": job_id,
                "institution_id": self.scf_institution.id,
                "process_type": "scf_no_row_tray_report",
            }

            try:
                self.storage_service.send_queue_message(
                    queue_name=NOTIFICATION_QUEUE, message_content=notification_message
                )
                logging.info("Report notification sent")
            except Exception as e:
                logging.error(f"Failed to send notification: {e}")
