"""Retrieve item from Alma API by barcode, store data in blob, and queue next action"""

import logging
from typing import Any, Literal

import azure.functions as func

from alma_item_checks_processor_service.config import (
    FETCH_ITEM_QUEUE,
    STORAGE_CONNECTION_SETTING_NAME,
)
from alma_item_checks_processor_service.services.processor_service import (
    ProcessorService,
)

bp: func.Blueprint = func.Blueprint()

logger = logging.getLogger(__name__)


@bp.function_name("process_item_data")
@bp.queue_trigger(
    arg_name="barcodemsg",
    queue_name=FETCH_ITEM_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME,
)
def process_item_data(barcodemsg: func.QueueMessage) -> None:
    """Retrieve item from Alma API by barcode, store data in blob, and queue next action

    Incoming message structure:
        {
            "institution": Institution object,
            "barcode": barcode string,
        }

    Args:
        barcodemsg (func.QueueMessage): Queue message
    """
    try:
        logger.info(
            f"🚀 TRACE: Starting process_item_data with message: {barcodemsg.get_body()}"
        )

        processor_service: ProcessorService = ProcessorService(
            barcodemsg
        )  # initialize service
        logger.info("✅ TRACE: ProcessorService initialized")

        item_data: dict[str, Any] | None = (
            processor_service.get_item_by_barcode()
        )  # retrieve item by barcode
        logger.info(
            f"📦 TRACE: Retrieved item_data: {bool(item_data)} (has data: {item_data is not None})"
        )

        if not item_data:  # If no item data, no further processing
            logger.warning("❌ TRACE: No item data retrieved, stopping processing")
            return

        # Check if item needs processing
        processing_list: list[Any] | Literal[True] | None = (
            processor_service.should_process(item_data)
        )
        logger.info(
            f"🔍 TRACE: Processing check result: {processing_list} (type: {type(processing_list)})"
        )

        if not processing_list or isinstance(
            processing_list, bool
        ):  # If no processes to run, return
            logger.info("⏭️  TRACE: No processing needed, stopping")
            return

        logger.info(
            f"🔄 TRACE: Starting processing loop for {len(processing_list)} items"
        )
        for i, processing_item in enumerate(
            processing_list
        ):  # Iterate through the flagged processes
            logger.info(
                f"⚙️  TRACE: Processing item {i+1}/{len(processing_list)}: {processing_item}"
            )
            processor_service.process(item_data, [processing_item])  # run the process
            logger.info(f"✅ TRACE: Completed processing item {i+1}")

        logger.info("🎉 TRACE: All processing completed successfully")

    except Exception as e:
        logger.error(
            f"💥 TRACE ERROR: process_item_data failed: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise
