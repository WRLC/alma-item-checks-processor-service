"""Service for processing IZ no row tray reports"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.config import (
    IZ_NO_ROW_TRAY_STAGE_TABLE,
    IZ_NO_ROW_TRAY_BATCH_QUEUE,
    IZ_NO_ROW_TRAY_BATCH_SIZE,
    STORAGE_CONNECTION_STRING,
)
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services.institution_service import (
    InstitutionService,
)
from alma_item_checks_processor_service.services.iz_item_processor import (
    IZItemProcessor,
)
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.models import Institution


# noinspection PyMethodMayBeStatic
class IZNoRowTrayReportService:
    """Service for processing IZ no row tray staged items and generating reports"""

    def __init__(self) -> None:
        self.storage_service: StorageService = StorageService(
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

    def process_staged_items_report(self) -> None:
        """Main method to initiate batch processing of staged items"""
        logging.info("Starting IZ no row tray batch processing")

        # Check if a job is already running (simple UUID-based check for IZ)
        if self._is_job_already_running():
            logging.info("IZ batch job already in progress, skipping this execution")
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
            f"IZ no row tray batch processing initiated. Job ID: {job_id}, "
            f"Total items: {len(staged_entities)}, "
            f"Batches: {(len(staged_entities) + IZ_NO_ROW_TRAY_BATCH_SIZE - 1) // IZ_NO_ROW_TRAY_BATCH_SIZE}"
        )

    def _get_staged_items(self) -> list[dict[str, Any]]:
        """Retrieve all staged items from staging table"""
        try:
            staged_entities: list[dict[str, Any]] | None = (
                self.storage_service.get_entities(
                    table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                    filter_query="PartitionKey eq 'iz_no_row_tray'",
                )
            )
            return staged_entities or []
        except Exception as e:
            logging.error(f"Failed to query staged items: {e}")
            return []

    def _process_single_item(
        self, barcode: str, institution_code: str
    ) -> dict[str, Any]:
        """Process a single staged item"""
        # Get institution
        with SessionMaker() as db:
            institution_service: InstitutionService = InstitutionService(db)
            institution: Institution | None = (
                institution_service.get_institution_by_code(institution_code)
            )

        if not institution:
            return {
                "success": False,
                "reason": f"Institution {institution_code} not found in database",
            }

        # Re-retrieve item from Alma
        item: Item | None = BaseItemProcessor.retrieve_item_by_barcode(
            institution, barcode
        )
        if not item:
            return {"success": False, "reason": "Item not found in Alma"}

        # Create parsed_item structure for processor
        parsed_item: dict[str, Any] = {
            "institution_code": institution_code,
            "item_data": item,
        }

        # Check if item should still be processed
        processor: IZItemProcessor = IZItemProcessor(parsed_item)
        if not processor.no_row_tray_should_process():
            return {"success": False, "reason": "No longer meets processing criteria"}

        # Process item - this updates the item with SCF data, stores in container, and queues for update
        updated: bool = processor.no_row_tray_report_process()
        if updated:
            return {"success": True}
        else:
            return {"success": False, "reason": "Failed to update item with SCF data"}

    def _is_job_already_running(self) -> bool:
        """Check if there's already an IZ batch job in progress using storage table"""
        try:
            # Use the stage table to store a simple lock record
            lock_entities = self.storage_service.get_entities(
                table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                filter_query="PartitionKey eq 'iz_batch_lock' and RowKey eq 'current_job'",
            )

            if lock_entities and len(lock_entities) > 0:
                # Check if lock is stale (older than 30 minutes)
                lock_entity = lock_entities[0]
                lock_time_str = lock_entity.get("created_at", "")

                if lock_time_str:
                    try:
                        lock_time = datetime.fromisoformat(
                            lock_time_str.replace("Z", "+00:00")
                        )
                        if datetime.now(timezone.utc) - lock_time > timedelta(
                            minutes=30
                        ):
                            # Lock is stale, remove it
                            self.storage_service.delete_entity(
                                table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                                partition_key="iz_batch_lock",
                                row_key="current_job",
                            )
                            return False
                    except ValueError:
                        # Invalid timestamp, treat as stale
                        return False

                logging.info("IZ batch job lock found, another job is in progress")
                return True

            # Create a lock
            lock_record = {
                "PartitionKey": "iz_batch_lock",
                "RowKey": "current_job",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "locked",
            }

            self.storage_service.upsert_entity(
                table_name=IZ_NO_ROW_TRAY_STAGE_TABLE, entity=lock_record
            )

            return False

        except Exception as e:
            logging.error(f"Failed to check/create IZ job lock: {e}")
            # If we can't check, assume no job is running to avoid blocking
            return False

    def _create_batch_job(self, total_items: int) -> str:
        """Create a batch job record using a simple in-memory tracking approach"""
        job_id = str(uuid.uuid4())
        total_batches = (
            total_items + IZ_NO_ROW_TRAY_BATCH_SIZE - 1
        ) // IZ_NO_ROW_TRAY_BATCH_SIZE

        logging.info(
            f"Created IZ batch job {job_id} for {total_items} items in {total_batches} batches"
        )
        return job_id

    def _enqueue_batches(
        self, staged_entities: list[dict[str, Any]], job_id: str
    ) -> None:
        """Split staged items into batches and enqueue for processing"""
        for i in range(0, len(staged_entities), IZ_NO_ROW_TRAY_BATCH_SIZE):
            batch = staged_entities[i : i + IZ_NO_ROW_TRAY_BATCH_SIZE]
            batch_number = (i // IZ_NO_ROW_TRAY_BATCH_SIZE) + 1

            # Extract barcodes and institution codes from entities
            batch_items = []
            for entity in batch:
                barcode = entity.get("RowKey")
                institution_code = entity.get("institution_code")
                if barcode and institution_code:
                    batch_items.append(
                        {"barcode": barcode, "institution_code": institution_code}
                    )

            batch_message = {
                "job_id": job_id,
                "batch_number": batch_number,
                "items": batch_items,
            }

            try:
                self.storage_service.send_queue_message(
                    queue_name=IZ_NO_ROW_TRAY_BATCH_QUEUE, message_content=batch_message
                )
                logging.info(
                    f"Enqueued IZ batch {batch_number} with {len(batch_items)} items"
                )
            except Exception as e:
                logging.error(f"Failed to enqueue IZ batch {batch_number}: {e}")
                # Continue with other batches even if one fails

    def process_batch(
        self, job_id: str, batch_number: int, items: list[dict[str, str]]
    ) -> None:
        """Process a single batch of IZ items"""
        logging.info(
            f"Processing IZ batch {batch_number} for job {job_id} with {len(items)} items"
        )

        processed_count = 0
        failed_count = 0

        for item in items:
            barcode = item["barcode"]
            institution_code = item["institution_code"]

            logging.info(
                f"Processing IZ item: {barcode} from institution {institution_code}"
            )
            result = self._process_single_item(barcode, institution_code)

            if result["success"]:
                processed_count += 1
                logging.info(f"Successfully processed IZ item {barcode}")
            else:
                failed_count += 1
                logging.warning(
                    f"Failed to process IZ item {barcode}: {result['reason']}"
                )

        # Clear processed items from staging table
        self._clear_batch_from_staging(items)

        # Check if this was the last batch and remove lock if so
        self._cleanup_job_lock_if_complete()

        logging.info(
            f"Completed IZ batch {batch_number}: {processed_count} processed, {failed_count} failed"
        )

    def _clear_batch_from_staging(self, items: list[dict[str, str]]) -> None:
        """Clear specific items from staging table"""
        for item in items:
            barcode = item["barcode"]
            try:
                self.storage_service.delete_entity(
                    table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                    partition_key="iz_no_row_tray",
                    row_key=barcode,
                )
            except Exception as e:
                logging.warning(f"Failed to remove staged IZ item {barcode}: {e}")

    def _cleanup_job_lock_if_complete(self) -> None:
        """Remove job lock if no more staged items remain"""
        try:
            # Check if there are any remaining staged items
            remaining_items = self.storage_service.get_entities(
                table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                filter_query="PartitionKey eq 'iz_no_row_tray'",
            )

            if not remaining_items or len(remaining_items) == 0:
                # No more staged items, remove the lock
                self.storage_service.delete_entity(
                    table_name=IZ_NO_ROW_TRAY_STAGE_TABLE,
                    partition_key="iz_batch_lock",
                    row_key="current_job",
                )
                logging.info("All IZ items processed, removed job lock")

        except Exception as e:
            logging.warning(f"Failed to cleanup IZ job lock: {e}")
