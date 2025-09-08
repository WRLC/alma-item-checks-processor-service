"""SCF Duplicates Service"""
import logging
from datetime import datetime, timezone
from typing import Any

from wrlc_alma_api_client import AlmaApiClient  # type: ignore
from wrlc_alma_api_client.models import AnalyticsReportResults  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_processor_service.config import (
    NOTIFICATION_QUEUE,
    REPORTS_CONTAINER,
)
from alma_item_checks_processor_service.database import SessionMaker
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.services import InstitutionService


# noinspection PyMethodMayBeStatic
class ScfDuplicatesService:
    """SCF Duplicates Service"""
    def process_scf_duplicates_report(self):
        """Retrieve SCF Duplicates Analytics Analysis and generate report."""
        with SessionMaker() as session:
            institution_service: InstitutionService = InstitutionService(session)
            institution: Institution = institution_service.get_institution_by_code('scf')

        report_id: str = f"scf_duplicate_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        alma_client: AlmaApiClient = AlmaApiClient(institution.api_key, "NA", timeout=250)  # get Alma client

        try:
            report: AnalyticsReportResults = alma_client.analytics.get_report(institution.duplicate_report_path)
        except Exception as e:
            logging.error(f"Job {report_id}: Error retrieving report: {e}")
            return

        if not report.rows:
            logging.info(f"Job {report_id}: No results found.")
            return

        storage_service = StorageService()  # get storage service

        storage_service.upload_blob_data(  # upload report to notifier container
            container_name=REPORTS_CONTAINER,
            blob_name=f"{report_id}.json",
            data=report.rows
        )

        notification_message: dict[str, Any] = {
            "report_id": report_id,
            "institution_id": institution.id,
            "process_type": "scf_duplicates"
        }

        storage_service.send_queue_message(  # send message to notifier queue
            queue_name=NOTIFICATION_QUEUE,
            message_content=notification_message
        )
