"""Retrieve item from Alma API by barcode, store data in blob, and queue next action"""
from typing import Any

import azure.functions as func
from wrlc_alma_api_client.models import Item  # type: ignore

from alma_item_checks_processor_service.config import BARCODE_RETRIEVAL_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from alma_item_checks_processor_service.services.processor_service import ProcessorService

bp: func.Blueprint = func.Blueprint()


@bp.function_name("process_item_data")
@bp.queue_trigger(
    arg_name="barcodemsg",
    queue_name=BARCODE_RETRIEVAL_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def process_item_data(barcodemsg: func.QueueMessage) -> None:
    """Retrieve item from Alma API by barcode, store data in blob, and queue next action

    Incoming message structure:
        {
            "institution": Institution object,
            "barcode": barcode string,
            "process": process string,
        }

    Args:
        barcodemsg (func.QueueMessage): Queue message
    """

    processor_service: ProcessorService = ProcessorService(barcodemsg)  # initialize service

    item_data: dict[str, Any] | None = processor_service.get_item_by_barcode()  # retrieve item by barcode

    if not item_data:  # If no item data, no further processing
        return

    processing_list: list | None = processor_service.should_process(item_data)  # Check if item needs processing

    if not processing_list:  # If no processes to run, return
        return

    for processing_item in processing_list:  # Iterate through the flagged processes
        processor_service.process(item_data, processing_item)  # run the process
