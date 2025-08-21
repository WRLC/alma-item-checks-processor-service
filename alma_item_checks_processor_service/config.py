import os

STORAGE_CONNECTION_SETTING_NAME = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

FETCH_QUEUE = os.getenv("FETCH_QUEUE", "fetch-queue")
SCF_NO_X_QUEUE = os.getenv("SCF_NO_X_QUEUE", "scf-no-x-queue")
SCF_NO_ROW_TRAY_QUEUE = os.getenv("SCF_NO_ROW_TRAY_QUEUE", "scf-no-row-tray-queue")
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "notification-queue")

SCF_NO_X_CONTAINER = os.getenv("SCF_NO_X_CONTAINER", "scf-no-x-container")
SCF_NO_ROW_TRAY_CONTAINER = os.getenv("SCF_NO_ROW_TRAY_CONTAINER", "scf-no-row-tray-container")

SCF_NO_ROW_TRAY_STAGE_TABLE = os.getenv("SCF_NO_ROW_TRAY_STAGE_TABLE", "scfnorowtraystagetable")
SCF_NO_ROW_TRAY_REPORT_TABLE = os.getenv("SCF_NO_ROW_TRAY_REPORT_TABLE", "scfnorowtrayreporttable")

API_CLIENT_TIMEOUT = int(os.getenv("API_CLIENT_TIMEOUT", 90))

# --- Business Logic Constants ---
PROVENANCE = [
    'Property of American University',
    'Property of American University Law School',
    'Property of Catholic University of America',
    'Property of Gallaudet University',
    'Property of George Mason University',
    'Property of George Washington Himmelfarb',
    'Property of George Washington University',
    'Property of George Washington University School of Law',
    'Property of Georgetown University',
    'Property of Georgetown University School of Law',
    'Property of Howard University',
    'Property of Marymount University',
    'Property of National Security Archive',
    'Property of University of the District of Columbia',
    'Property of University of the District of Columbia Jazz Archives',
]

EXCLUDED_NOTES = [
    'At WRLC waiting to be processed',
    'DO NOT DELETE',
    'WD'
]

SKIP_LOCATIONS = [
    "WRLC Gemtrac Drawer",
    "WRLC Microfilm Cabinet",
    "WRLC Microfiche Cabinet",
    "Low Temperature Media Preservation Unit  # 1 @ SCF"
]