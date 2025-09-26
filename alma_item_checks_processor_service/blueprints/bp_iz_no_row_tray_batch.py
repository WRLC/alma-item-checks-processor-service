"""Process individual IZ no row tray batches"""

import json
import logging
import azure.functions as func

from alma_item_checks_processor_service.config import IZ_NO_ROW_TRAY_BATCH_QUEUE
from alma_item_checks_processor_service.services.iz_no_row_tray_report_service import (
    IZNoRowTrayReportService,
)

bp: func.Blueprint = func.Blueprint()


# noinspection PyUnusedLocal
@bp.function_name("process_iz_no_row_tray_batch")
@bp.queue_trigger(
    arg_name="msg",
    queue_name=IZ_NO_ROW_TRAY_BATCH_QUEUE,
    connection="AzureWebJobsStorage",
)
def process_iz_no_row_tray_batch(msg: func.QueueMessage) -> None:
    """Process a single batch of IZ no row tray items

    Args:
        msg (func.QueueMessage): Queue message containing batch details
    """
    try:
        # Parse message content
        message_content = json.loads(msg.get_body().decode("utf-8"))
        job_id = message_content.get("job_id")
        batch_number = message_content.get("batch_number")
        items = message_content.get("items", [])

        logging.info(
            f"Processing IZ batch {batch_number} for job {job_id} with {len(items)} items"
        )

        # Process the batch
        report_service = IZNoRowTrayReportService()
        report_service.process_batch(job_id, batch_number, items)

        logging.info(f"Completed processing IZ batch {batch_number} for job {job_id}")

    except Exception as e:
        logging.error(f"Failed to process IZ no row tray batch: {e}")
        raise
