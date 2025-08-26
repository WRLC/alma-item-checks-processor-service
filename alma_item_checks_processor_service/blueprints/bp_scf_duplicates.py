"""Timer trigger to fetch duplicate barcodes from the Alma API for SCF."""
import azure.functions as func

from alma_item_checks_processor_service.config import SCF_DUPLICATES_REPORT_NCRON
from alma_item_checks_processor_service.services import ScfDuplicatesService

bp: func.Blueprint = func.Blueprint()


# noinspection PyUnusedLocal
@bp.function_name("process_scf_duplicates_report")
@bp.timer_trigger(
    schedule=SCF_DUPLICATES_REPORT_NCRON,
    arg_name="timer"
)
def process_scf_duplicates_report(timer: func.TimerRequest) -> None:
    """Retrieve SCF Duplicates Analytics Analysis and generate report.

    Args:
        timer (func.TimerRequest): Timer trigger request
    """
    scf_duplicates_service: ScfDuplicatesService = ScfDuplicatesService()
    scf_duplicates_service.process_scf_duplicates_report()
