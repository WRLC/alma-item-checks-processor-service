"""Tests for services/iz_item_processor.py"""

import pytest
from unittest.mock import Mock, patch
from alma_item_checks_processor_service.services.iz_item_processor import IZItemProcessor


class TestIZItemProcessor:
    """Test cases for IZItemProcessor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_item = Mock()
        self.mock_item.item_data.barcode = "12345"
        self.mock_item.item_data.location.value = "wrlc"
        self.mock_item.holding_data.temp_location.value = None

        self.parsed_item = {
            "institution_code": "doc",
            "item_data": self.mock_item
        }
        self.processor = IZItemProcessor(self.parsed_item)

    def test_init(self):
        """Test IZItemProcessor initialization"""
        assert self.processor.parsed_item == self.parsed_item

    @patch('alma_item_checks_processor_service.services.iz_item_processor.CHECKED_IZ_LOCATIONS', ['wrlc', 'test'])
    def test_no_row_tray_should_process_valid_location(self):
        """Test no_row_tray_should_process with valid location"""
        with patch.object(self.processor, 'no_row_tray_data', return_value=True), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=False):

            result = self.processor.no_row_tray_should_process()

        assert result is True

    @patch('alma_item_checks_processor_service.services.iz_item_processor.CHECKED_IZ_LOCATIONS', ['other'])
    def test_no_row_tray_should_process_invalid_location(self):
        """Test no_row_tray_should_process with invalid location"""
        result = self.processor.no_row_tray_should_process()
        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.CHECKED_IZ_LOCATIONS', ['temp_loc'])
    def test_no_row_tray_should_process_valid_temp_location(self):
        """Test no_row_tray_should_process with valid temp location"""
        self.mock_item.item_data.location.value = "other"
        self.mock_item.holding_data.temp_location.value = "temp_loc"

        with patch.object(self.processor, 'no_row_tray_data', return_value=True), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=False):

            result = self.processor.no_row_tray_should_process()

        assert result is True

    def test_no_row_tray_should_process_no_institution(self):
        """Test no_row_tray_should_process with no institution code"""
        self.parsed_item["institution_code"] = None
        result = self.processor.no_row_tray_should_process()
        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.CHECKED_IZ_LOCATIONS', ['wrlc'])
    def test_no_row_tray_should_process_no_issues(self):
        """Test no_row_tray_should_process when no row/tray issues"""
        with patch.object(self.processor, 'no_row_tray_data', return_value=False), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=False):

            result = self.processor.no_row_tray_should_process()

        assert result is False

    def test_should_process_with_row_tray_issues(self):
        """Test should_process when item has row/tray issues"""
        with patch.object(self.processor, 'no_row_tray_should_process', return_value=True):
            result = self.processor.should_process()

        assert result == ["iz_no_row_tray"]

    def test_should_process_no_issues(self):
        """Test should_process when item has no issues"""
        with patch.object(self.processor, 'no_row_tray_should_process', return_value=False):
            result = self.processor.should_process()

        assert result == []

    def test_process_method(self):
        """Test process method calls appropriate processor"""
        processes = ["iz_no_row_tray"]

        with patch.object(self.processor, 'no_row_tray_process') as mock_no_row_tray:
            self.processor.process(processes)

        mock_no_row_tray.assert_called_once()

    def test_process_method_unknown_process(self):
        """Test process method with unknown process type"""
        processes = ["unknown_process"]

        with patch.object(self.processor, 'no_row_tray_process') as mock_no_row_tray:
            self.processor.process(processes)

        mock_no_row_tray.assert_not_called()

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.iz_item_processor.IZ_NO_ROW_TRAY_STAGE_TABLE', 'test_table')
    def test_no_row_tray_process_success(self, mock_storage_service_class):
        """Test successful no_row_tray_process"""
        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        self.processor.no_row_tray_process()

        expected_entity = {
            "PartitionKey": "iz_no_row_tray",
            "RowKey": "12345",
            "institution_code": "doc",
        }

        mock_storage_service.upsert_entity.assert_called_once_with(
            table_name="test_table",
            entity=expected_entity
        )

    def test_no_row_tray_process_no_institution(self):
        """Test no_row_tray_process with no institution code"""
        self.parsed_item["institution_code"] = None

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            self.processor.no_row_tray_process()

        # Should return early without calling storage

    def test_no_row_tray_process_no_barcode(self):
        """Test no_row_tray_process with no barcode"""
        self.mock_item.item_data.barcode = ""

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            self.processor.no_row_tray_process()

        # Should return early without calling storage

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_get_scf_item_by_barcode_success(self, mock_session_maker):
        """Test successful SCF item retrieval"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_scf_item = Mock()

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.BaseItemProcessor.retrieve_item_by_barcode',
                   return_value=mock_scf_item):

            result = self.processor._get_scf_item_by_barcode("12345X")

        assert result == mock_scf_item
        mock_institution_service.get_institution_by_code.assert_called_with("scf")

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_get_scf_item_by_barcode_fallback_to_scf_psb(self, mock_session_maker):
        """Test SCF item retrieval with fallback to scf-psb"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.side_effect = [None, Mock()]  # First call returns None, second returns institution

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.BaseItemProcessor.retrieve_item_by_barcode') as mock_retrieve:

            self.processor._get_scf_item_by_barcode("12345X")

        # Should try scf first, then scf-psb
        assert mock_institution_service.get_institution_by_code.call_count == 2
        mock_institution_service.get_institution_by_code.assert_any_call("scf")
        mock_institution_service.get_institution_by_code.assert_any_call("scf-psb")

    def test_scf_item_has_correct_row_tray_data_valid(self):
        """Test _scf_item_has_correct_row_tray_data with valid data"""
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "R01M02S03"
        mock_scf_item.item_data.internal_note_1 = None

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._scf_item_has_correct_row_tray_data(mock_scf_item)

        assert result is True

    def test_scf_item_has_correct_row_tray_data_invalid(self):
        """Test _scf_item_has_correct_row_tray_data with invalid data"""
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "INVALID"
        mock_scf_item.item_data.internal_note_1 = "ALSO_INVALID"

        result = self.processor._scf_item_has_correct_row_tray_data(mock_scf_item)

        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_no_row_tray_report_process_success(self, mock_session_maker):
        """Test successful no_row_tray_report_process"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "R01M02S03"

        with patch.object(self.processor, '_get_scf_item_by_barcode', return_value=mock_scf_item), \
             patch.object(self.processor, '_scf_item_has_correct_row_tray_data', return_value=True), \
             patch.object(self.processor, '_update_iz_item_with_scf_data', return_value=True), \
             patch.object(self.processor, '_handle_successful_update'), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):

            result = self.processor.no_row_tray_report_process()

        assert result is True

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_no_row_tray_report_process_scf_item_not_found(self, mock_session_maker):
        """Test no_row_tray_report_process when SCF item not found"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch.object(self.processor, '_get_scf_item_by_barcode', return_value=None), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):

            result = self.processor.no_row_tray_report_process()

        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_no_row_tray_report_process_scf_item_no_correct_data(self, mock_session_maker):
        """Test no_row_tray_report_process when SCF item has no correct row/tray data"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        mock_scf_item = Mock()

        with patch.object(self.processor, '_get_scf_item_by_barcode', return_value=mock_scf_item), \
             patch.object(self.processor, '_scf_item_has_correct_row_tray_data', return_value=False), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):

            result = self.processor.no_row_tray_report_process()

        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_no_row_tray_report_process_update_failed(self, mock_session_maker):
        """Test no_row_tray_report_process when IZ item update fails"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        mock_scf_item = Mock()

        with patch.object(self.processor, '_get_scf_item_by_barcode', return_value=mock_scf_item), \
             patch.object(self.processor, '_scf_item_has_correct_row_tray_data', return_value=True), \
             patch.object(self.processor, '_update_iz_item_with_scf_data', return_value=False), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):

            result = self.processor.no_row_tray_report_process()

        assert result is False

    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_get_scf_item_by_barcode_no_institution_found(self, mock_session_maker):
        """Test _get_scf_item_by_barcode when no SCF institution found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):

            result = self.processor._get_scf_item_by_barcode("12345X")

        assert result is None

    def test_scf_item_has_correct_row_tray_data_alt_call_number_valid(self):
        """Test _scf_item_has_correct_row_tray_data with valid alt call number"""
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "R01M02S03"
        mock_scf_item.item_data.internal_note_1 = None

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._scf_item_has_correct_row_tray_data(mock_scf_item)

        assert result is True

    def test_scf_item_has_correct_row_tray_data_internal_note_valid(self):
        """Test _scf_item_has_correct_row_tray_data with valid internal note"""
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = None
        mock_scf_item.item_data.internal_note_1 = "R05M10S15"

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._scf_item_has_correct_row_tray_data(mock_scf_item)

        assert result is True

    def test_scf_item_has_correct_row_tray_data_no_valid_data(self):
        """Test _scf_item_has_correct_row_tray_data with no valid data"""
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "INVALID"
        mock_scf_item.item_data.internal_note_1 = "ALSO_INVALID"

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._scf_item_has_correct_row_tray_data(mock_scf_item)

        assert result is False

    def test_update_iz_item_with_scf_data_alt_call_number(self):
        """Test _update_iz_item_with_scf_data copying from alt call number"""
        mock_iz_item = Mock()
        mock_iz_item.item_data.alternative_call_number = None
        mock_iz_item.item_data.internal_note_1 = None

        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "R01M02S03"
        mock_scf_item.item_data.internal_note_1 = None

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._update_iz_item_with_scf_data(mock_iz_item, mock_scf_item)

        assert result is True
        assert mock_iz_item.item_data.alternative_call_number == "R01M02S03"

    def test_update_iz_item_with_scf_data_internal_note(self):
        """Test _update_iz_item_with_scf_data copying from internal note"""
        mock_iz_item = Mock()
        mock_iz_item.item_data.alternative_call_number = None
        mock_iz_item.item_data.internal_note_1 = None

        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = None
        mock_scf_item.item_data.internal_note_1 = "R05M10S15"

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._update_iz_item_with_scf_data(mock_iz_item, mock_scf_item)

        assert result is True
        assert mock_iz_item.item_data.internal_note_1 == "R05M10S15"

    def test_update_iz_item_with_scf_data_with_invalid_data(self):
        """Test _update_iz_item_with_scf_data when SCF has invalid row/tray data"""
        mock_iz_item = Mock()
        mock_iz_item.item_data.alternative_call_number = None
        mock_iz_item.item_data.internal_note_1 = None

        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "INVALID"
        mock_scf_item.item_data.internal_note_1 = "ALSO_INVALID"

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._update_iz_item_with_scf_data(mock_iz_item, mock_scf_item)

        assert result is True
        assert mock_iz_item.item_data.alternative_call_number == "INVALID"
        assert mock_iz_item.item_data.internal_note_1 == "ALSO_INVALID"

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_handle_successful_update(self, mock_session_maker, mock_storage_service_class):
        """Test _handle_successful_update method"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor._handle_successful_update(mock_item, "iz_no_row_tray")

        # Verify storage operations
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    def test_handle_successful_update_no_institution_code(self, mock_storage_service_class):
        """Test _handle_successful_update with no institution code"""
        mock_item = Mock()

        # Set parsed_item to have no institution code
        processor = IZItemProcessor({"institution_code": None, "item_data": mock_item})

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging') as mock_logging:
            processor._handle_successful_update(mock_item, "iz_no_row_tray")

        # Should log error and return early
        mock_logging.error.assert_called()
        mock_storage_service_class.assert_not_called()

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    def test_handle_successful_update_blob_upload_error(self, mock_storage_service_class):
        """Test _handle_successful_update with blob upload error"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}

        mock_storage_service = Mock()
        mock_storage_service.upload_blob_data.side_effect = ValueError("Upload failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch.object(self.processor, 'generate_job_id', return_value="test_job_123"), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging') as mock_logging:

            self.processor._handle_successful_update(mock_item, "iz_no_row_tray")

        # Should log error and return early
        mock_logging.error.assert_called()
        mock_storage_service.send_queue_message.assert_not_called()

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_handle_successful_update_institution_not_found(self, mock_session_maker, mock_storage_service_class):
        """Test _handle_successful_update when institution not found in database"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging') as mock_logging:

            self.processor._handle_successful_update(mock_item, "iz_no_row_tray")

        # Should log error and return early
        mock_logging.error.assert_called()
        mock_storage_service.send_queue_message.assert_not_called()

    @patch('alma_item_checks_processor_service.services.iz_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.iz_item_processor.SessionMaker')
    def test_handle_successful_update_queue_send_error(self, mock_session_maker, mock_storage_service_class):
        """Test _handle_successful_update with queue send error"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service.send_queue_message.side_effect = TypeError("Queue failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.iz_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"), \
             patch('alma_item_checks_processor_service.services.iz_item_processor.logging') as mock_logging:

            self.processor._handle_successful_update(mock_item, "iz_no_row_tray")

        # Should log error for queue send failure
        mock_logging.error.assert_called()
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    def test_update_iz_item_with_scf_data_exception(self):
        """Test _update_iz_item_with_scf_data handles exceptions"""
        # Create mock items - make the SCF data evaluation cause an exception
        iz_item = Mock()

        scf_item = Mock()
        # Make the boolean evaluation or string access raise an exception
        scf_item.item_data.alternative_call_number = Mock()
        scf_item.item_data.alternative_call_number.__bool__ = Mock(side_effect=Exception("Test error"))

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging') as mock_logging:
            result = self.processor._update_iz_item_with_scf_data(iz_item, scf_item)

        # Should return False and log error
        assert result is False
        mock_logging.error.assert_called()

    def test_update_iz_item_with_scf_data_success(self):
        """Test successful IZ item update with SCF data"""
        mock_iz_item = Mock()
        mock_scf_item = Mock()
        mock_scf_item.item_data.alternative_call_number = "R01M02S03"
        mock_scf_item.item_data.internal_note_1 = "Note"

        with patch('alma_item_checks_processor_service.services.iz_item_processor.logging'):
            result = self.processor._update_iz_item_with_scf_data(mock_iz_item, mock_scf_item)

        assert result is True
        assert mock_iz_item.item_data.alternative_call_number == "R01M02S03"
        assert mock_iz_item.item_data.internal_note_1 == "Note"
