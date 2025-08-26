"""Processor Service for Alma Item Checks"""
import azure.functions as func
from alma_item_checks_processor_service.blueprints.bp_processor import bp as bp_processor
from alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray import bp as bp_scf_no_row_tray
from alma_item_checks_processor_service.blueprints.bp_iz_no_row_tray import bp as bp_iz_no_row_tray
from alma_item_checks_processor_service.blueprints.bp_scf_duplicates import bp as bp_scf_duplicates

app = func.FunctionApp()

app.register_blueprint(bp_processor)
app.register_blueprint(bp_scf_no_row_tray)
app.register_blueprint(bp_iz_no_row_tray)
app.register_blueprint(bp_scf_duplicates)
