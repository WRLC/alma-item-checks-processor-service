"""Base class for all item processors"""
import logging
import re
from abc import ABC
import uuid
from datetime import datetime, timezone
from typing import Any

from wrlc_alma_api_client.models import Item

from alma_item_checks_processor_service.config import SKIP_LOCATIONS


class BaseItemProcessor(ABC):
    """Base class for all item processors"""
    def __init__(self, parsed_item: dict[str, Any]):
        self.parsed_item = parsed_item

    def no_row_tray_data(self) -> bool:
        """Check if item has missing row/tray data

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")
        alt_call_number: str | None = item.item_data.alternative_call_number  # get alt call number
        barcode: str = item.item_data.barcode

        if alt_call_number is None:  # if no alt call number, process
            logging.warning(
                f'ProcessorService.no_row_tray_data: Item {barcode} Alternative Call Number is not set. Processing.'
            )
            return True

        logging.info(f'ProcessorService.no_row_tray_data: Item {barcode} Alternative Call Number is set. Skipping.')
        return False

    def wrong_row_tray_data(self, iz: str) -> bool:
        """Check if SCF item has wrong row/tray data

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode
        fields_to_check: list[dict[str, str]] = [  # set up list of field dicts to check
            {
                "label": "Alt Call Number",
                "value": item.item_data.alternative_call_number
            },
            {
                "label": "Internal Note 1",
                "value": item.item_data.internal_note_1
            }
        ]

        pattern: str = r"^R.*M.*S"  # regex for correct row/tray data format

        for field in fields_to_check:  # check both fields

            field_value: str | None = field.get('value')

            if field_value is not None and field_value.strip() != '':  # only process if the field has value set

                if iz == "scf":
                    if any(loc in field_value for loc in SKIP_LOCATIONS):  # check if in skipped location
                        logging.info(
                            msg=f'ProcessorService.scf_wrong_row_tray_data: Skipping field with value "{field_value}" '
                                f'for item {barcode} because it contains a skipped location.')
                        continue

                if re.search(pattern=pattern, string=field_value) is None:  # check if call number matches format
                    logging.warning(
                        f'ProcessorService.scf_wrong_row_tray_data: Item {barcode} {field.get("label")} '
                        'in incorrect format. Processing.'
                    )
                    return True

        logging.info(msg='SCFNoRowTray.wrong_row_tray_data: All set fields in correct format. Skipping.')
        return False

    def generate_job_id(self, process_name: str) -> str:
        """Generate a job ID"""
        iz: str = self.parsed_item.get("institution_code")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        job_id = f"{iz}_{process_name}_{timestamp}_{unique_id}"

        return job_id
