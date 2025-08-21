"""Service to handle barcode events"""
import json
import logging
import re
import uuid
from datetime import datetime, timezone

import azure.core.exceptions
import time
from typing import Any

import azure.functions as func
from requests import RequestException
from wrlc_alma_api_client import AlmaApiClient  # type: ignore
from wrlc_alma_api_client.exceptions import AlmaApiError  # type: ignore
from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService

from alma_item_checks_processor_service.config import (
    API_CLIENT_TIMEOUT,
    EXCLUDED_NOTES,
    PROVENANCE,
    SKIP_LOCATIONS, SCF_NO_X_QUEUE, SCF_NO_X_CONTAINER
)
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.services import InstitutionService


# noinspection PyMethodMayBeStatic
class ProcessorService:
    """Service to handle barcode events"""
    def __init__(self, barcodemsg: func.QueueMessage) -> None:
        """Initialize the BarcodeService class

        Args:
            barcodemsg (func.QueueMessage): Queue message
        """
        self.barcodemsg: func.QueueMessage = barcodemsg

    def get_item_by_barcode(self) -> Item | None:
        """Get item by barcode

        Returns:
            Item: The item data if found, None otherwise
        """
        barcode_data: dict[str, Any] = self.parse_barcode_data()  # parse message

        if not barcode_data:
            return None

        inst: Institution | None = self.get_institution(barcode_data.get("institution_code"))  # get institution object

        if not inst:  # if no institution or barcode, return nothing
            return None

        item_data: Item | None = self.retrieve_item(inst, barcode_data.get("barcode"))  # get item data from Alma

        parsed_item_data: dict[str, Any] | None = {
            "barcode": barcode_data.get("barcode"),
            "institution_code": barcode_data.get("institution_code"),
            "item_data": item_data,
            "process": barcode_data.get("process"),
        }

        return parsed_item_data

    def should_process(self, item_data: dict[str, Any]) -> list[str] | None:
        """Check if barcode should be processed

        Args:
            item_data (dict[str, Any]): Item data

        Returns:
            list[str] | None: list of checks to run or False if none
        """
        iz: str | None = item_data.get("institution_code")  # get IZ code

        if iz.lower() == 'scf':  # if IZ is SCF, use SCF check
            should_process: list[str] | bool = self.scf_should_process(item_data)

            if not should_process:  # If doesn't meet SCF check criteria, don't process
                return None

            return should_process

        should_process: list[str] | bool = self.iz_should_process(item_data)  # if not SCF, use IZ check

        if not should_process:  # If doesn't meet IZ check criteria, don't process
            return None

        return should_process

    def process(self, item_data: dict[str, Any], processes: list[str]) -> None:
        """Process item data

        Args:
            item_data (dict[str, Any]): Item data
            processes (list[str]): List of processes to run
        """
        iz: str | None = item_data.get("institution_code")  # get IZ code

        if iz.lower() == 'scf':  # If SCF IZ
            self.scf_process(item_data, processes)  # run SCF processes

        self.iz_process(item_data, processes)

    def parse_barcode_data(self) -> dict[str, Any] | None:
        """Parse barcode data
        """
        raw_barcode_data: dict[str, Any] = json.loads(self.barcodemsg.get_body().decode())  # get barcode data

        institution_code: str | None = raw_barcode_data.get("institution")  # get institution code
        barcode: str | None = raw_barcode_data.get("barcode")  # get barcode

        if not institution_code or not barcode:  # If institution code or barcode missing, log error and return
            logging.error("RequestService.parse_barcode_data: Missing institution or barcode")
            return None

        barcode_data: dict[str, Any] = {  # create dict for API call
            "institution_code": institution_code,  # institution code
            "barcode": barcode  # barcode
        }

        return barcode_data

    def get_institution(self, code: str) -> Institution | None:
        """Get institution by code

        Args:
            code (str): The institution code

        Returns:
            Institution | None: The institution if found, None otherwise
        """
        with SessionMaker() as db:  # make database session
            institution_service: InstitutionService = InstitutionService(db)  # initialize InstitutionService
            institution: Institution | None = institution_service.get_institution_by_code(code=code)  # get institution

        return institution

    def retrieve_item(self, inst: Institution, barcode: str, max_retries: int = 3) -> Item | None:
        """Retrieve item from Alma API

        Args:
            inst (Institution): The institution instance
            barcode (str): The barcode
            max_retries (int): The maximum number of retries

        Returns:
            Item | None: The item if found, None otherwise
        """
        barcode_data: dict[str, Any] = self.parse_barcode_data()  # get barcode and IZ from queue message

        alma_client: AlmaApiClient = AlmaApiClient(  # initialize Alma API client
            api_key=str(inst.api_key),  # API key
            region='NA',  # Alma region
            timeout=API_CLIENT_TIMEOUT  # HTTP request timeout time
        )

        item_data: Item | None = None  # initialize empty Item object

        for attempt in range(max_retries):  # iterate through retries
            try:
                item_data: Item | None = alma_client.items.get_item_by_barcode(barcode=barcode)  # Get item from Alma
                break  # Success, exit the loop
            except RequestException as e:  # Catches timeouts, connection errors, etc.
                logging.warning(
                    f"Attempt {attempt + 1}/{max_retries} to get item {barcode_data["barcode"]} "
                    f"failed with a network error: {e}"
                )
                if attempt < max_retries - 1:  # If there are retries left, wait and retry
                    time.sleep(2 * (attempt + 1))  # Wait 2, then 4 seconds before retrying
                else:
                    logging.error(  # If no data after all retries log error and return nothing
                        f"All {max_retries} retry attempts failed for barcode {barcode_data["barcode"]}. "
                        f"Skipping processing."
                    )
                    return None
            except AlmaApiError as e:  # If non-retriable API error (e.g., 404 Not Found), log and return nothing
                logging.warning(f"Error retrieving item {barcode_data["barcode"]} from Alma, skipping processing: {e}")
                return None

        if not item_data:  # If there's no item data, log and return nothing
            logging.info(
                f"ProcessorService.retrieve_item: Item {barcode_data["barcode"]} not active in Alma, "
                "skipping further processing"
            )
            return None

        return item_data

    def scf_should_process(self, parsed_item_data: dict[str, Any]) -> list[str] | None:
        """Check if SCF item should be processed

        Args:
            parsed_item_data (dict[str, Any]): Item data

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        item_data: Item = parsed_item_data.get("item_data")  # item object
        barcode: str = item_data.item_data.barcode  # item barcode

        should_process: list[str] = []  # initialize empty list of processes

        if not self.scf_shared_checks(item_data, barcode):  # If doesn't meet basic criteria, stop processiong
            return None

        if self.scf_no_x_should_process(barcode):  # If barcode doesn't end in X...
            should_process.append('scf_no_x')  # ...flag for processing

        if self.scf_no_row_tray_should_process(item_data, barcode):  # If missing/wrong row/tray info...
            should_process.append('scf_no_row_tray_data')  # ...flag for processing

        if self.scf_withdrawn_should_process(item_data, barcode):  # If item marked withdrawn...
            should_process.append('scf_withdrawn_data')   # ...flag for processing

        return should_process

    def iz_should_process(self, item_data: dict[str, Any]) -> list[str] | None:
        """Check if IZ item should be processed

        Args:
            item_data (dict[str, Any]): Item data
        """
        # TODO: Entire method
        return None

    def scf_process(self, item_data: dict[str, Any], processes: list[str]) -> None:
        """Process SCF item

        Args:
            item_data (dict[str, Any]): Item data
            processes (list[str]): Processes to run
        """
        for process in processes:  # iterate through the flagged processes
            if process == "scf_no_x":  # fix missing X from barcode and notify
                self.scf_no_x_process(item_data)
            if process == "scf_no_row_tray_data":  # stage problem row/tray data for report
                self.scf_no_row_tray_process(item_data)
            if process == "scf_withdrawn_data":  # notify to confirm withdrawn item
                self.scf_withdrawn_process(item_data)

    def iz_process(self, item_data: dict[str, Any], processes: list[str]) -> None:
        """Process IZ item

        Args:
            item_data (dict[str, Any]): Item data
            processes (list[str]): Processes to run
        """
        # TODO: Entire method

    def scf_shared_checks(self, item_data: Item, barcode: str) -> bool:
        """Check if SCF item doesn't meet conditions for any checks

        Args:
            item_data (Item): The item data
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        if (  # If in discard temporary location, don't process
            item_data.holding_data.temp_location.value and
            'discard' in item_data.holding_data.temp_location.value.lower()
        ):
            logging.info(f"Item {barcode} is in a discard temporary location, skipping processing")
            return False

        if (  # If in discard location, don't process
            'discard' in item_data.item_data.location.value.lower()
        ):
            logging.info(f"Item {barcode} is in a discard location, skipping processing")
            return False

        if (  # If not a checked provenance, don't process
            not item_data.item_data.provenance or item_data.item_data.provenance.desc not in PROVENANCE
        ):
            logging.info(f"Item {barcode} has no checked provenance, skipping processing")
            return False

        return True

    def scf_no_x_should_process(self, barcode: str) -> bool:
        """Check if SCF item ends in X

        Args:
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        if not barcode.endswith("X"):  # check if barcode ends in X
            logging.warning(f"ProcessorService.scf_no_x_should_process: barcode {barcode} does not end with X.")
            return True

        return False

    def scf_no_x_process(self, item_data: dict[str, Any]) -> None:
        """Process SCF item with missing X in barcode

        Args:
            item_data (dict[str, Any]): Item data
        """
        job_id: str = self.generate_job_id('scf_no_x')  # generate a unique job ID

        barcode: str = item_data.get("item_data").item_data.barcode  # get barcode value
        item_data.get("item_data").item_data.barcode = barcode + "X"  # append X to barcode

        storage_service: StorageService = StorageService()  # initialize storage service

        try:
            storage_service.upload_blob_data(  # upload item data dict blob
                container_name=SCF_NO_X_CONTAINER,  # container
                blob_name=job_id + ".json",  # blob name
                data=json.dumps(item_data).encode()  # data
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return

        try:
            storage_service.send_queue_message(  # send claim ticket
                queue_name=SCF_NO_X_QUEUE,  # queue
                message_content={"job_id": job_id}  # message
            )
        except (ValueError, TypeError, azure.core.exceptions.ServiceRequestError):
            return

    def scf_no_row_tray_should_process(self, item_data: Item, barcode: str) -> bool:
        """Check if SCF item has missing or incorrect row/tray data

        Args:
            item_data (Item): The item data
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        if (  # If row/tray data is missing or wrong, process
            self.scf_no_row_tray_data(item_data, barcode) or self.scf_wrong_row_tray_data(item_data, barcode)
        ):
            # If internal note 1 is in the list of excluded notes, don't process
            if item_data.item_data.internal_note_1.lower().strip() in (item.lower().strip() for item in EXCLUDED_NOTES):
                return False
            return True
        return False

    def scf_no_row_tray_process(self, item_data: dict[str, Any]) -> None:
        """Process SCF item with missing or incorrect row tray data

        Args:
            item_data (Item): The item data
        """
        # TODO: Entire method

    def scf_no_row_tray_data(self, item_data: Item, barcode: str) -> bool:
        """Check if SCF item has missing row/tray data
        Args:
            item_data (Item): The item data
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        alt_call_number: str | None = item_data.item_data.alternative_call_number  # get alt call number

        if alt_call_number is None:  # if no alt call number, process
            logging.warning(
                f'ProcessorService.scf_no_row_tray_data: Item {barcode} Alternative Call Number is not set. Processing.'
            )
            return True

        logging.info(f'ProcessorService.scf_no_row_tray_data: Item {barcode} Alternative Call Number is set. Skipping.')
        return False

    def scf_wrong_row_tray_data(self, item_data: Item, barcode: str) -> bool:
        """Check if SCF item has wrong row/tray data

        Args:
            item_data (Item): The item data
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        fields_to_check: list[dict[str, str]] = [  # set up list of field dicts to check
            {
                "label": "Alt Call Number",
                "value": item_data.item_data.alternative_call_number
            },
            {
                "label": "Internal Note 1",
                "value": item_data.item_data.internal_note_1
            }
        ]

        pattern: str = r"^R.*M.*S"  # regex for correct row/tray data format

        for field in fields_to_check:  # check both fields

            field_value: str | None = field.get('value')

            if field_value is not None and field_value.strip() != '':  # only process if the field has value set

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

    def scf_withdrawn_should_process(self, item_data: Item, barcode: str) -> bool:
        """Check if SCF item has withdrawal data

        Args:
            item_data (Item): The item data
            barcode (str): The barcode

        Returns:
            bool: True if SCF should be processed, False otherwise
        """
        # TODO: Entire method
        return False

    def scf_withdrawn_process(self, item_data: dict[str, Any]) -> None:
        """Process SCF item with withdrawal data

        Args:
            item_data (Item): The item data
        """
        # TODO: Entire method

    def generate_job_id(self, process_name: str) -> str:
        """Generate a job ID

        Args:
            process_name (str): The name of the process
        Returns:
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        job_id = f"job_{process_name}_{timestamp}_{unique_id}"

        return job_id
