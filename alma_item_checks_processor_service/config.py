import os

STORAGE_CONNECTION_SETTING_NAME = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

BARCODE_RETRIEVAL_QUEUE = os.getenv("BARCODE_RETRIEVAL_QUEUE", "barcode-retrieval-queue")

API_CLIENT_TIMEOUT = int(os.getenv("API_CLIENT_TIMEOUT", 90))

ITEM_VALIDATION_QUEUE = os.getenv("ITEM_VALIDATION_QUEUE", "item-validation-queue")
ITEM_VALIDATION_CONTAINER = os.getenv("ITEM_VALIDATION_CONTAINER", "item-validation")

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