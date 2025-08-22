"""Service to handle barcode events"""
import json
import logging
import time
from typing import Any

import azure.functions as func
from requests import RequestException
from wrlc_alma_api_client import AlmaApiClient  # type: ignore
from wrlc_alma_api_client.exceptions import AlmaApiError  # type: ignore
from wrlc_alma_api_client.models import Item  # type: ignore

from alma_item_checks_processor_service.config import API_CLIENT_TIMEOUT
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.services.institution_service import InstitutionService
from alma_item_checks_processor_service.services.iz_item_processor import IZItemProcessor
from alma_item_checks_processor_service.services.scf_item_processor import SCFItemProcessor


# noinspection PyMethodMayBeStatic
class ProcessorService:
    """Service to handle barcode events"""
    def __init__(self, barcodemsg: func.QueueMessage) -> None:
        """Initialize the BarcodeService class

        Args:
            barcodemsg (func.QueueMessage): Queue message
        """
        self.barcodemsg: func.QueueMessage = barcodemsg

    def get_item_by_barcode(self) -> dict[str, Any] | None:
        """Get item by barcode

        Returns:
            Item: The item data if found, None otherwise
        """
        barcode_retrieval_data: dict[str, Any] = self.get_barcode_retrieval_data()  # parse message

        if not barcode_retrieval_data:
            return None

        inst: Institution | None = self.get_institution(  # get institution object
            barcode_retrieval_data.get("institution_code")
        )

        if not inst:  # if no institution or barcode, return nothing
            return None

        item: Item | None = self.retrieve_item(inst, barcode_retrieval_data.get("barcode"))  # get item data from Alma

        parsed_item: dict[str, Any] | None = {
            "institution_code": inst.code,
            "item_data": item,
            "process": barcode_retrieval_data.get("process"),
        }

        return parsed_item

    def should_process(self, parsed_item: dict[str, Any]) -> list[str] | None:
        """Check if barcode should be processed

        Args:
            parsed_item (dict[str, Any]): Item data

        Returns:
            list[str] | None: list of checks to run or False if none
        """
        iz: str | None = parsed_item.get("institution_code")  # get IZ code

        if iz.lower() == 'scf':  # if IZ is SCF, use SCF check
            scf_processor = SCFItemProcessor(parsed_item)
            should_process: list[str] | bool = scf_processor.should_process()

            if not should_process:  # If doesn't meet SCF check criteria, don't process
                return None

            return should_process

        iz_processor = IZItemProcessor(parsed_item)
        should_process: list[str] | bool = iz_processor.should_process()  # if not SCF, use IZ check

        if not should_process:  # If doesn't meet IZ check criteria, don't process
            return None

        return should_process

    def process(self, parsed_item: dict[str, Any], processes: list[str]) -> None:
        """Process item data

        Args:
            parsed_item (dict[str, Any]): Item data
            processes (list[str]): List of processes to run
        """
        iz: str | None = parsed_item.get("institution_code")  # get IZ code

        if iz.lower() == 'scf':  # If SCF IZ
            scf_processor = SCFItemProcessor(parsed_item)
            scf_processor.process(processes)  # run SCF processes

        iz_processor = IZItemProcessor(parsed_item)
        iz_processor.process(processes)

    def get_barcode_retrieval_data(self) -> dict[str, Any] | None:
        """Parse fetch item queue message
        """
        message_data: dict[str, Any] = json.loads(self.barcodemsg.get_body().decode())  # get barcode data

        institution_code: str | None = message_data.get("institution")  # get institution code
        barcode: str | None = message_data.get("barcode")  # get barcode
        process: str | None = message_data.get("process")

        if not institution_code or not barcode:  # If institution code or barcode missing, log error and return
            logging.error("RequestService.parse_barcode_data: Missing institution or barcode")
            return None

        barcode_retrieval_data: dict[str, Any] = {  # create dict for API call
            "institution_code": institution_code,  # institution code
            "barcode": barcode,  # barcode
            "process": process  # process
        }

        return barcode_retrieval_data

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
                    f"Attempt {attempt + 1}/{max_retries} to get item {barcode} "
                    f"failed with a network error: {e}"
                )
                if attempt < max_retries - 1:  # If there are retries left, wait and retry
                    time.sleep(2 * (attempt + 1))  # Wait 2, then 4 seconds before retrying
                else:
                    logging.error(  # If no data after all retries log error and return nothing
                        f"All {max_retries} retry attempts failed for barcode {barcode}. "
                        f"Skipping processing."
                    )
                    return None
            except AlmaApiError as e:  # If non-retriable API error (e.g., 404 Not Found), log and return nothing
                logging.warning(f"Error retrieving item {barcode} from Alma, skipping processing: {e}")
                return None

        if not item_data:  # If there's no item data, log and return nothing
            logging.info(
                f"ProcessorService.retrieve_item: Item {barcode} not active in Alma, "
                "skipping further processing"
            )
            return None

        return item_data
