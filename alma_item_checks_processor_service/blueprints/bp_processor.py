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
        processor_service: ProcessorService = ProcessorService(
            barcodemsg
        )  # initialize service

        item_data: dict[str, Any] | None = (
            processor_service.get_item_by_barcode()
        )  # retrieve item by barcode

        if not item_data:  # If no item data, no further processing
            return

        # Check if item needs processing
        processing_list: list[Any] | Literal[True] | None = (
            processor_service.should_process(item_data)
        )

        if not processing_list or isinstance(
            processing_list, bool
        ):  # If no processes to run, return
            return

        for i, processing_item in enumerate(
            processing_list
        ):  # Iterate through the flagged processes
            processor_service.process(item_data, [processing_item])  # run the process

    except Exception as e:
        logger.error(
            f"process_item_data failed: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise
