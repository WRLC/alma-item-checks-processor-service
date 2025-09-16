"""Processor Service for Alma Item Checks"""
import logging
import os
from datetime import datetime

import azure.functions as func
from alma_item_checks_processor_service.blueprints.bp_processor import bp as bp_processor
from alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray import bp as bp_scf_no_row_tray
from alma_item_checks_processor_service.blueprints.bp_iz_no_row_tray import bp as bp_iz_no_row_tray
from alma_item_checks_processor_service.blueprints.bp_scf_duplicates import bp as bp_scf_duplicates
from alma_item_checks_processor_service.blueprints.bp_institutions_api import bp as bp_institutions_api

# Set up file logging for local development only
if os.getenv("AZURE_FUNCTIONS_ENVIRONMENT") != "Production":
    log_filename = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add to your app's logger
    logger = logging.getLogger('alma_item_checks_processor_service')
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    print(f"📝 Local development: Trace logging enabled to file: {log_filename}")

app = func.FunctionApp()

app.register_blueprint(bp_processor)
app.register_blueprint(bp_scf_no_row_tray)
app.register_blueprint(bp_iz_no_row_tray)
app.register_blueprint(bp_scf_duplicates)
#app.register_blueprint(bp_institutions_api)
