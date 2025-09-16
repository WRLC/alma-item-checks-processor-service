"""Tests for services/base_processor.py"""

import pytest
from unittest.mock import Mock, patch
from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor


class TestBaseItemProcessor:
    """Test cases for BaseItemProcessor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.parsed_item = {
            "institution_code": "test",
            "item_data": Mock()
        }
        self.processor = BaseItemProcessor(self.parsed_item)

    def test_init(self):
        """Test BaseItemProcessor initialization"""
        assert self.processor.parsed_item == self.parsed_item

    def test_no_row_tray_data_none_alt_call_number(self):
        """Test no_row_tray_data with None alternative_call_number"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = None
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.no_row_tray_data()

        assert result is True

    def test_no_row_tray_data_empty_alt_call_number(self):
        """Test no_row_tray_data with empty string alternative_call_number"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = "   "
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.no_row_tray_data()

        assert result is True

    def test_no_row_tray_data_with_valid_alt_call_number(self):
        """Test no_row_tray_data with valid alternative_call_number"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = "R01M02S03"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.no_row_tray_data()

        assert result is False

    def test_generate_job_id(self):
        """Test generate_job_id method"""
        self.processor.parsed_item = {"institution_code": "test"}

        with patch('alma_item_checks_processor_service.services.base_processor.datetime') as mock_datetime, \
             patch('alma_item_checks_processor_service.services.base_processor.uuid') as mock_uuid:

            mock_datetime.now.return_value.strftime.return_value = "20250916120000"
            mock_uuid.uuid4.return_value = Mock()
            mock_uuid.uuid4.return_value.__str__ = Mock(return_value="abcd1234-5678-9012-3456-789012345678")

            result = self.processor.generate_job_id("test_process")

            assert result == "test_test_process_20250916120000_abcd1234"

    def test_wrong_row_tray_data_with_correct_format(self):
        """Test wrong_row_tray_data with correct format data"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = "R01M02S03"
        mock_item.item_data.internal_note_1 = "R05M10S15"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.wrong_row_tray_data("scf")

        assert result is False

    def test_wrong_row_tray_data_with_incorrect_format(self):
        """Test wrong_row_tray_data with incorrect format data"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = "Invalid format"
        mock_item.item_data.internal_note_1 = None
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.wrong_row_tray_data("scf")

        assert result is True

    def test_wrong_row_tray_data_with_skip_location(self):
        """Test wrong_row_tray_data with skip location in SCF"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = "WRLC Gemtrac Drawer"
        mock_item.item_data.internal_note_1 = None
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.wrong_row_tray_data("scf")

        assert result is False

    def test_wrong_row_tray_data_with_empty_fields(self):
        """Test wrong_row_tray_data with empty field values"""
        mock_item = Mock()
        mock_item.item_data.alternative_call_number = ""
        mock_item.item_data.internal_note_1 = None
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.wrong_row_tray_data("scf")

        assert result is False

    @patch('alma_item_checks_processor_service.services.base_processor.time')
    @patch('alma_item_checks_processor_service.services.base_processor.AlmaApiClient')
    def test_retrieve_item_by_barcode_success(self, mock_alma_client_class, mock_time):
        """Test successful item retrieval"""
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.code = "test"

        mock_alma_client = Mock()
        mock_alma_client_class.return_value = mock_alma_client

        mock_item = Mock()
        mock_item.bib_data.mms_id = "123456789"
        mock_alma_client.items.get_item_by_barcode.return_value = mock_item

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.retrieve_item_by_barcode(mock_institution, "12345")

        assert result == mock_item
        mock_alma_client.items.get_item_by_barcode.assert_called_once_with("12345")

    @patch('alma_item_checks_processor_service.services.base_processor.time')
    @patch('alma_item_checks_processor_service.services.base_processor.AlmaApiClient')
    def test_retrieve_item_by_barcode_network_error_retry_success(self, mock_alma_client_class, mock_time):
        """Test item retrieval with network error then success on retry"""
        from requests.exceptions import RequestException

        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.code = "test"

        mock_alma_client = Mock()
        mock_alma_client_class.return_value = mock_alma_client

        mock_item = Mock()
        mock_item.bib_data.mms_id = "123456789"
        # First call fails, second succeeds
        mock_alma_client.items.get_item_by_barcode.side_effect = [
            RequestException("Network error"),
            mock_item
        ]

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.retrieve_item_by_barcode(mock_institution, "12345")

        assert result == mock_item
        assert mock_alma_client.items.get_item_by_barcode.call_count == 2
        mock_time.sleep.assert_called_once_with(2)

    @patch('alma_item_checks_processor_service.services.base_processor.time')
    @patch('alma_item_checks_processor_service.services.base_processor.AlmaApiClient')
    def test_retrieve_item_by_barcode_network_error_all_retries_fail(self, mock_alma_client_class, mock_time):
        """Test item retrieval with network errors on all retries"""
        from requests.exceptions import RequestException

        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.code = "test"

        mock_alma_client = Mock()
        mock_alma_client_class.return_value = mock_alma_client

        # All calls fail
        mock_alma_client.items.get_item_by_barcode.side_effect = RequestException("Network error")

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.retrieve_item_by_barcode(mock_institution, "12345", max_retries=3)

        assert result is None
        assert mock_alma_client.items.get_item_by_barcode.call_count == 3
        assert mock_time.sleep.call_count == 2  # Sleeps before retry 2 and 3

    @patch('alma_item_checks_processor_service.services.base_processor.AlmaApiClient')
    def test_retrieve_item_by_barcode_alma_api_error(self, mock_alma_client_class):
        """Test item retrieval with Alma API error (404 etc.)"""
        from wrlc_alma_api_client.exceptions import AlmaApiError

        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.code = "test"

        mock_alma_client = Mock()
        mock_alma_client_class.return_value = mock_alma_client

        # API error (e.g., 404 Not Found)
        mock_alma_client.items.get_item_by_barcode.side_effect = AlmaApiError("Item not found")

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.retrieve_item_by_barcode(mock_institution, "12345")

        assert result is None
        mock_alma_client.items.get_item_by_barcode.assert_called_once()

    @patch('alma_item_checks_processor_service.services.base_processor.AlmaApiClient')
    def test_retrieve_item_by_barcode_no_item_data(self, mock_alma_client_class):
        """Test item retrieval when no item data returned"""
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.code = "test"

        mock_alma_client = Mock()
        mock_alma_client_class.return_value = mock_alma_client

        # No item returned
        mock_alma_client.items.get_item_by_barcode.return_value = None

        with patch('alma_item_checks_processor_service.services.base_processor.logging'):
            result = self.processor.retrieve_item_by_barcode(mock_institution, "12345")

        assert result is None
