"""Base class for all item processors"""

import logging
import re
import time
from abc import ABC
import uuid
from datetime import datetime, timezone
from typing import Any

from wrlc_alma_api_client import AlmaApiClient  # type: ignore
from wrlc_alma_api_client.exceptions import AlmaApiError  # type: ignore
from wrlc_alma_api_client.models import Item  # type: ignore
from requests import RequestException

from alma_item_checks_processor_service.config import SKIP_LOCATIONS, API_CLIENT_TIMEOUT
from alma_item_checks_processor_service.models import Institution


class BaseItemProcessor(ABC):
    """Base class for all item processors"""

    def __init__(self, parsed_item: dict[str, Any]):
        self.parsed_item = parsed_item

    def no_row_tray_data(self) -> bool:
        """Check if item has missing row/tray data

        Returns:
            bool: True if SCF should be processed, False otherwise

        Raises:
            KeyError: If required item data fields are missing
            AttributeError: If item data structure is invalid
        """
        item: Item = self.parsed_item.get("item_data")
        alt_call_number: str | None = (
            item.item_data.alternative_call_number
        )  # get alt call number
        barcode: str = item.item_data.barcode

        if alt_call_number is None or (
            isinstance(alt_call_number, str) and alt_call_number.strip() == ""
        ):  # if no alt call number, process
            logging.warning(
                f"ProcessorService.no_row_tray_data: Item {barcode} Alternative Call Number is not set. Processing."
            )
            return True

        logging.info(
            f"ProcessorService.no_row_tray_data: Item {barcode} Alternative Call Number is set to '{alt_call_number}'. Skipping."
        )
        return False

    def wrong_row_tray_data(self, iz: str) -> bool:
        """Check if SCF item has wrong row/tray data

        Args:
            iz (str): Institution zone code

        Returns:
            bool: True if SCF should be processed, False otherwise

        Raises:
            KeyError: If required item data fields are missing
            AttributeError: If item data structure is invalid
        """
        item: Item = self.parsed_item.get("item_data")
        barcode: str = item.item_data.barcode
        fields_to_check: list[dict[str, str]] = [  # set up list of field dicts to check
            {
                "label": "Alt Call Number",
                "value": item.item_data.alternative_call_number,
            },
            {"label": "Internal Note 1", "value": item.item_data.internal_note_1},
        ]

        pattern: str = r"^R.*M.*S"  # regex for correct row/tray data format

        for field in fields_to_check:  # check both fields
            field_value: str | None = field.get("value")

            if (
                field_value is not None and field_value.strip() != ""
            ):  # only process if the field has value set
                if iz == "scf":
                    if any(
                        loc in field_value for loc in SKIP_LOCATIONS
                    ):  # check if in skipped location
                        logging.info(
                            msg=f'ProcessorService.scf_wrong_row_tray_data: Skipping field with value "{field_value}" '
                            f"for item {barcode} because it contains a skipped location."
                        )
                        continue

                if (
                    re.search(pattern=pattern, string=field_value) is None
                ):  # check if call number matches format
                    logging.warning(
                        f'ProcessorService.scf_wrong_row_tray_data: Item {barcode} {field.get("label")} '
                        'in incorrect format. Processing.'
                    )
                    return True

        logging.info(
            msg="SCFNoRowTray.wrong_row_tray_data: All set fields in correct format. Skipping."
        )
        return False

    def generate_job_id(self, process_name: str) -> str:
        """Generate a job ID"""
        iz: str | None = self.parsed_item.get("institution_code")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        job_id = f"{iz}_{process_name}_{timestamp}_{unique_id}"

        return job_id

    @staticmethod
    def retrieve_item_by_barcode(
        institution: Institution, barcode: str, max_retries: int = 3
    ) -> Item | None:
        """Retrieve item from Alma API by barcode

        Args:
            institution (Institution): The institution instance
            barcode (str): The barcode
            max_retries (int): The maximum number of retries

        Returns:
            Item | None: The item if found, None otherwise

        Raises:
            AlmaApiError: If Alma API returns an error response
            RequestException: If network request fails after all retries
            ValueError: If institution API key is invalid
        """
        logger = logging.getLogger(__name__)
        alma_client: AlmaApiClient = AlmaApiClient(
            api_key=str(institution.api_key), region="NA", timeout=API_CLIENT_TIMEOUT
        )

        item_data: Item | None = None

        for attempt in range(max_retries):
            try:
                item_data = alma_client.items.get_item_by_barcode(barcode)
                break  # Success, exit the loop
            except RequestException as e:  # Catches timeouts, connection errors, etc.
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} to get item {barcode} "
                    f"failed with a network error: {e}"
                )
                if (
                    attempt < max_retries - 1
                ):  # If there are retries left, wait and retry
                    wait_time = 2 * (attempt + 1)
                    time.sleep(wait_time)  # Wait 2, then 4 seconds before retrying
                else:
                    logger.error(
                        f"All {max_retries} retry attempts failed for barcode {barcode}. "
                        f"Skipping processing."
                    )
                    return None
            except AlmaApiError as e:  # If non-retriable API error (e.g., 404 Not Found), log and return nothing
                logger.warning(
                    f"Error retrieving item {barcode} from Alma, skipping processing: {e}"
                )
                return None

        if not item_data:
            logger.info(
                f"Item {barcode} not active in Alma, skipping further processing"
            )
            return None

        return item_data
