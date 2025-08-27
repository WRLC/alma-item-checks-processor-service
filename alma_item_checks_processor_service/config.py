"""Configuration file for alma_item_checks_processor_service."""
import os

STORAGE_CONNECTION_SETTING_NAME = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

FETCH_ITEM_QUEUE = os.getenv("FETCH_QUEUE", "fetch-item-queue")
UPDATE_QUEUE = os.getenv("UPDATE_QUEUE", "update-queue")  # For items that need Alma updates
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "notification-queue")  # For staff notifications

UPDATED_ITEMS_CONTAINER = os.getenv("UPDATED_ITEMS_CONTAINER", "updated-items-container")  # All updated item data
REPORTS_CONTAINER = os.getenv("REPORTS_CONTAINER", "reports-container")  # Generated reports

SCF_NO_ROW_TRAY_STAGE_TABLE = os.getenv("SCF_NO_ROW_TRAY_STAGE_TABLE", "scfnorowtraystagetable")
SCF_NO_ROW_TRAY_REPORT_TABLE = os.getenv("SCF_NO_ROW_TRAY_REPORT_TABLE", "scfnorowtrayreporttable")
IZ_NO_ROW_TRAY_STAGE_TABLE = os.getenv("IZ_NO_ROW_TRAY_STAGE_TABLE", "iznorowtraystagetable")

IZ_NO_ROW_TRAY_NCRON = os.getenv("IZ_NO_ROW_TRAY_NCRON", "0 45 23 * * 0-4")
SCF_NO_ROW_TRAY_REPORT_NCRON = os.getenv("SCF_NO_ROW_TRAY_REPORT_NCRON", "0 30 23 * * 0-4")
SCF_DUPLICATES_REPORT_NCRON = os.getenv("SCF_DUPLICATES_REPORT_NCRON", "0 0 9 * * 1-5")

API_CLIENT_TIMEOUT = int(os.getenv("API_CLIENT_TIMEOUT", 90))

# --- Business Logic Constants ---
PROVENANCE = [
    {
        'label': 'AU',
        'value': 'Property of American University',
    },
    {
        'label': 'AULAW',
        'value': 'Property of American University Law School',
    },
    {
        'label': 'CU',
        'value': 'Property of Catholic University of America',
    },
    {
        'label': 'GA',
        'value': 'Property of Gallaudet University',
    },
    {
        'label': 'GMU',
        'value': 'Property of George Mason University',
    },
    {
        'label': 'HI',
        'value': 'Property of George Washington Himmelfarb',
    },
    {
        'label': 'GW',
        'value': 'Property of George Washington University',
    },
    {
        'label': 'GWLAW',
        'value': 'Property of George Washington University School of Law',
    },
    {
        'label': 'GT',
        'value': 'Property of Georgetown University',
    },
    {
        'label': 'GTLAW',
        'value': 'Property of Georgetown University School of Law',
    },
    {
        'label': 'HU',
        'value': 'Property of Howard University',
    },
    {
        'label': 'MU',
        'value': 'Property of Marymount University',
    },
    {
        'label': 'NSA',
        'value': 'Property of National Security Archive',
    },
    {
        'label': 'UDC',
        'value': 'Property of University of the District of Columbia',
    },
    {
        'label': 'UDCJAZZ',
        'value': 'Property of University of the District of Columbia Jazz Archives',
    },
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

CHECKED_IZ_LOCATIONS = [
    "auscfgen",
    "auscfspec",
    "auscfmus",
    "auscfgenp",
    "auscfcmc",
    "WRLC",
    "wrlc_shrd",
    "wrlc_cntr",
    "wrlc_shrp",
    "ofstr",
    "offs",
    "ocs",
    "ocsk",
    "ocskp",
    "ocsmf",
    "ocsmr",
    "ocsp",
    "ocspw",
    "ocssc",
    "ocst",
    "ocsv",
    "ocsvc",
    "ocswd",
    "huwrlc",
    "huwrlcdup",
    "huwrlcmicr",
    "huwrlcper",
    "huwrlcperm",
    "huwrlcret",
    "wrlc stor",
    "wrlc stru",
    "wrlc stnc",
    "wrlc shrp",
    "wrlc dism",
    "wrlc disp",
    "wrlc cstk",
    "wrlc dfbk",
    "wrlc dflm",
    "wrlc dfmd",
    "wrlc cgrc",
    "wrlc sgrc",
    "wrlcstoret",
    "wrlcstnret",
    "wrlc micro",
    "wrlcscfrs",
    "WRLC CAT",
    "WRLC SCF",
    "WRLCDIG",
    "wrlc",
    "wrlc almon",
    "wrlc alper",
    "wrlc cunc",
    "wrlc danc",
    "wrlc gtdp",
    "wrlc gtkib",
    "wrlc gtkip",
    "wrlc gtmo",
    "wrlc gtnc",
    "wrlc gtsp",
    "wrlc gtspe",
    "wrlc gtthe",
    "wrlc gtv",
    "wrlc gtvc",
    "wrlc hida",
    "wrlc himm",
    "wrlc resv",
    "wrlc shrm",
    "wrlc snsa",
    "wrlc test",
    "wrlc test2",
    "wrlc wood",
    "wrlc woodc",
    "wrlc_ebks",
    "wrlc_rstcd",
    "wrlc_video",
    "wrlccunc",
    "wrlcstndup",
    "wrlcstodup",
    "wrlcstrret"
]
