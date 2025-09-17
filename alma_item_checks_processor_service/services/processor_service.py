"""Service to handle barcode events"""

import json
import logging
from typing import Any, Literal

import azure.functions as func
from wrlc_alma_api_client.models import Item  # type: ignore

from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.services.institution_service import (
    InstitutionService,
)
from alma_item_checks_processor_service.services.iz_item_processor import (
    IZItemProcessor,
)
from alma_item_checks_processor_service.services.scf_item_processor import (
    SCFItemProcessor,
)


# noinspection PyMethodMayBeStatic
class ProcessorService:
    """Service to handle barcode events"""

    def __init__(self, barcodemsg: func.QueueMessage) -> None:
        """Initialize the BarcodeService class

        Args:
            barcodemsg (func.QueueMessage): Queue message
        """
        self.barcodemsg: func.QueueMessage = barcodemsg
        self.logger = logging.getLogger(__name__)

    def get_item_by_barcode(self) -> dict[str, Any] | None:
        """Get item by barcode

        Returns:
            Item: The item data if found, None otherwise
        """
        try:
            barcode_retrieval_data: dict[str, Any] | None = (
                self.get_barcode_retrieval_data()
            )  # parse message

            if not barcode_retrieval_data:
                return None

            inst: Institution | None = self.get_institution(  # get institution object
                barcode_retrieval_data.get("institution_code")  # type: ignore
            )

            if not inst:  # if no institution or barcode, return nothing
                return None

            barcode = barcode_retrieval_data.get("barcode")

            item: Item | None = BaseItemProcessor.retrieve_item_by_barcode(
                inst,
                barcode,  # type: ignore
            )

            parsed_item: dict[str, Any] | None = {
                "institution_code": inst.code,
                "item_data": item,
            }

            return parsed_item

        except Exception as e:
            self.logger.error(
                f"get_item_by_barcode failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

    def should_process(
        self, parsed_item: dict[str, Any]
    ) -> list[str] | Literal[True] | None:
        """Check if barcode should be processed

        Args:
            parsed_item (dict[str, Any]): Item data

        Returns:
            list[str] | None: list of checks to run or False if none
        """
        try:
            iz: str | None = parsed_item.get("institution_code")  # get IZ code

            if iz is None:
                return None

            if iz.lower() in ["scf", "scf-psb"]:  # if IZ is SCF, use SCF check
                scf_processor = SCFItemProcessor(parsed_item)
                should_process: list[str] | bool = scf_processor.should_process()

                if (
                    not should_process
                ):  # If doesn't meet SCF check criteria, don't process
                    return None

                return should_process

            iz_processor = IZItemProcessor(parsed_item)
            should_process: list[str] | bool = iz_processor.should_process()  # type: ignore # if not SCF, use IZ check

            if not should_process:  # If doesn't meet IZ check criteria, don't process
                return None

            return should_process

        except Exception as e:
            self.logger.error(
                f"should_process failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

    def process(self, parsed_item: dict[str, Any], processes: list[str]) -> None:
        """Process item data

        Args:
            parsed_item (dict[str, Any]): Item data
            processes (list[str]): List of processes to run
        """
        try:
            iz: str | None = parsed_item.get("institution_code")  # get IZ code

            if iz is None:
                return

            if iz.lower() in ["scf", "scf-psb"]:  # If SCF IZ
                scf_processor = SCFItemProcessor(parsed_item)
                scf_processor.process(processes)  # run SCF processes
            else:
                iz_processor = IZItemProcessor(parsed_item)
                iz_processor.process(processes)

        except Exception as e:
            self.logger.error(
                f"process failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

    def get_barcode_retrieval_data(self) -> dict[str, Any] | None:
        """Parse fetch item queue message"""
        message_data: dict[str, Any] = json.loads(
            self.barcodemsg.get_body().decode()
        )  # get barcode data

        institution_code: str | None = message_data.get(
            "institution"
        )  # get institution code
        barcode: str | None = message_data.get("barcode")  # get barcode

        if (
            not institution_code or not barcode
        ):  # If institution code or barcode missing, log error and return
            logging.error(
                "RequestService.parse_barcode_data: Missing institution or barcode"
            )
            return None

        barcode_retrieval_data: dict[str, Any] = {  # create dict for API call
            "institution_code": institution_code,  # institution code
            "barcode": barcode,  # barcode
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
            institution_service: InstitutionService = InstitutionService(
                db
            )  # initialize InstitutionService
            institution: Institution | None = (
                institution_service.get_institution_by_code(code=code)
            )  # get institution

        return institution
