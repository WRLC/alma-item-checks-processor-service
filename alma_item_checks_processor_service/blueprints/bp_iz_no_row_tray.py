"""Process IZ no row tray staged items and generate reports"""
import azure.functions as func
from alma_item_checks_processor_service.services.iz_no_row_tray_report_service import IZNoRowTrayReportService

bp: func.Blueprint = func.Blueprint()


# noinspection PyUnusedLocal
@bp.function_name("process_iz_no_row_tray_report")
@bp.schedule(
    schedule="0 30 2 * * *",  # Daily at 2:30 AM UTC (30 minutes after SCF)
    arg_name="timer"
)
def process_iz_no_row_tray_report(timer: func.TimerRequest) -> None:
    """Process all IZ no row tray staged items and generate report
    
    Args:
        timer (func.TimerRequest): Timer trigger request
    """
    report_service: IZNoRowTrayReportService = IZNoRowTrayReportService()
    report_service.process_staged_items_report()
