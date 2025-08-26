"""Process SCF no row tray staged items and generate reports"""
import azure.functions as func
from alma_item_checks_processor_service.services.scf_no_row_tray_report_service import SCFNoRowTrayReportService

bp: func.Blueprint = func.Blueprint()


# noinspection PyUnusedLocal
@bp.function_name("process_scf_no_row_tray_report")
@bp.schedule(
    schedule="0 0 2 * * *",  # Daily at 2:00 AM UTC
    arg_name="timer"
)
def process_scf_no_row_tray_report(timer: func.TimerRequest) -> None:
    """Process all SCF no row tray staged items and generate report
    
    Args:
        timer (func.TimerRequest): Timer trigger request
    """
    report_service: SCFNoRowTrayReportService = SCFNoRowTrayReportService()
    report_service.process_staged_items_report()
