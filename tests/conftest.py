"""Pytest configuration and fixtures for alma-item-checks-processor-service tests"""

import pytest
from unittest.mock import Mock, patch
from alma_item_checks_processor_service.models.institution import Institution


@pytest.fixture
def mock_institution():
    """Create a mock Institution object"""
    institution = Mock(spec=Institution)
    institution.id = 1
    institution.name = "Test Institution"
    institution.code = "test"
    institution.api_key = "test_api_key"
    institution.duplicate_report_path = "/test/path"
    return institution


@pytest.fixture
def mock_alma_item():
    """Create a mock Alma Item object"""
    item = Mock()
    item.item_data.barcode = "12345"
    item.item_data.location.value = "main"
    item.item_data.alternative_call_number = None
    item.item_data.internal_note_1 = None
    item.item_data.provenance.desc = "Test Provenance"
    item.holding_data.temp_location.value = None
    item.bib_data.mms_id = "123456789"
    return item


@pytest.fixture
def parsed_item_data(mock_alma_item):
    """Create parsed item data structure"""
    return {
        "institution_code": "test",
        "item_data": mock_alma_item
    }


@pytest.fixture
def mock_storage_service():
    """Create a mock StorageService"""
    storage_service = Mock()
    storage_service.get_entities.return_value = []
    storage_service.upsert_entity.return_value = None
    storage_service.delete_entity.return_value = None
    storage_service.upload_blob_data.return_value = None
    storage_service.send_queue_message.return_value = None
    return storage_service


@pytest.fixture
def mock_session():
    """Create a mock database session"""
    session = Mock()
    return session


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for all tests"""
    env_vars = {
        'AzureWebJobsStorage': 'test_connection_string',
        'SQLALCHEMY_CONNECTION_STRING': 'mysql+pymysql://test:test@localhost/test',
        'API_CLIENT_TIMEOUT': '90',
        'FETCH_QUEUE': 'test-fetch-queue',
        'UPDATE_QUEUE': 'test-update-queue',
        'NOTIFICATION_QUEUE': 'test-notification-queue',
        'UPDATED_ITEMS_CONTAINER': 'test-updated-items',
        'REPORTS_CONTAINER': 'test-reports',
        'SCF_NO_ROW_TRAY_STAGE_TABLE': 'test-scf-stage',
        'SCF_NO_ROW_TRAY_REPORT_TABLE': 'test-scf-report',
        'IZ_NO_ROW_TRAY_STAGE_TABLE': 'test-iz-stage'
    }

    with patch.dict('os.environ', env_vars):
        yield
