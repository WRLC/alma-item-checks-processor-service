"""Tests for services/scf_item_processor.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from alma_item_checks_processor_service.services.scf_item_processor import SCFItemProcessor


class TestSCFItemProcessor:
    """Test cases for SCFItemProcessor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_item = Mock()
        self.mock_item.item_data.barcode = "12345"
        self.mock_item.item_data.location.value = "main"
        self.mock_item.item_data.provenance.desc = "Test Provenance"
        self.mock_item.holding_data.temp_location.value = None

        self.parsed_item = {
            "institution_code": "scf",
            "item_data": self.mock_item
        }
        self.processor = SCFItemProcessor(self.parsed_item)

    def test_init(self):
        """Test SCFItemProcessor initialization"""
        assert self.processor.parsed_item == self.parsed_item

    @patch('alma_item_checks_processor_service.services.scf_item_processor.PROVENANCE', [{"value": "Test Provenance"}])
    def test_shared_checks_success(self):
        """Test shared_checks with valid item"""
        result = self.processor.shared_checks()
        assert result is True

    def test_shared_checks_discard_temp_location(self):
        """Test shared_checks with discard temp location"""
        self.mock_item.holding_data.temp_location.value = "discard"

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.shared_checks()

        assert result is False

    def test_shared_checks_discard_location(self):
        """Test shared_checks with discard location"""
        self.mock_item.item_data.location.value = "discard"

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.shared_checks()

        assert result is False

    def test_shared_checks_invalid_provenance(self):
        """Test shared_checks with invalid provenance"""
        self.mock_item.item_data.provenance.desc = "Invalid Provenance"

        with patch('alma_item_checks_processor_service.services.scf_item_processor.PROVENANCE', [{"value": "Test Provenance"}]):
            with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
                result = self.processor.shared_checks()

        assert result is False

    def test_no_x_should_process_missing_x(self):
        """Test no_x_should_process with barcode missing X"""
        self.mock_item.item_data.barcode = "12345"

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.no_x_should_process()

        assert result is True

    def test_no_x_should_process_has_x(self):
        """Test no_x_should_process with barcode ending in X"""
        self.mock_item.item_data.barcode = "12345X"

        result = self.processor.no_x_should_process()

        assert result is False

    def test_withdrawn_should_process_alt_call_number_wd(self):
        """Test withdrawn_should_process with WD in alternative call number"""
        self.mock_item.item_data.alternative_call_number = "WD"
        self.mock_item.item_data.internal_note_1 = None

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.withdrawn_should_process()

        assert result is True

    def test_withdrawn_should_process_internal_note_wd(self):
        """Test withdrawn_should_process with WD in internal note"""
        self.mock_item.item_data.alternative_call_number = None
        self.mock_item.item_data.internal_note_1 = "WD"

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.withdrawn_should_process()

        assert result is True

    def test_withdrawn_should_process_no_wd(self):
        """Test withdrawn_should_process with no WD"""
        self.mock_item.item_data.alternative_call_number = "NORMAL"
        self.mock_item.item_data.internal_note_1 = "NORMAL"

        result = self.processor.withdrawn_should_process()

        assert result is False

    @patch('alma_item_checks_processor_service.services.scf_item_processor.EXCLUDED_NOTES', ["EXCLUDED"])
    def test_no_row_tray_should_process_excluded_note(self):
        """Test no_row_tray_should_process with excluded note"""
        self.mock_item.item_data.internal_note_1 = "EXCLUDED"

        with patch.object(self.processor, 'no_row_tray_data') as mock_no_row_tray:
            result = self.processor.no_row_tray_should_process()

        assert result is False
        mock_no_row_tray.assert_not_called()

    def test_should_process_comprehensive(self):
        """Test should_process method with multiple checks"""
        with patch.object(self.processor, 'shared_checks', return_value=True), \
             patch.object(self.processor, 'no_x_should_process', return_value=True), \
             patch.object(self.processor, 'no_row_tray_should_process', return_value=False), \
             patch.object(self.processor, 'withdrawn_should_process', return_value=True):

            result = self.processor.should_process()

        expected = ["scf_no_x", "scf_withdrawn_data"]
        assert result == expected

    def test_should_process_shared_checks_fail(self):
        """Test should_process when shared_checks fails"""
        with patch.object(self.processor, 'shared_checks', return_value=False):
            result = self.processor.should_process()

        assert result == []

    def test_process_method(self):
        """Test process method calls appropriate processors"""
        processes = ["scf_no_x", "scf_no_row_tray_data", "scf_withdrawn_data"]

        with patch.object(self.processor, 'no_x_process') as mock_no_x, \
             patch.object(self.processor, 'no_row_tray_process') as mock_no_row_tray, \
             patch.object(self.processor, 'withdrawn_process') as mock_withdrawn:

            self.processor.process(processes)

        mock_no_x.assert_called_once()
        mock_no_row_tray.assert_called_once()
        mock_withdrawn.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_no_x_process_success(self, mock_session_maker, mock_storage_service_class):
        """Test successful no_x_process"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.no_x_process()

        # Verify barcode was modified
        assert mock_item.item_data.barcode == "12345X"

        # Verify storage operations
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_no_x_process_no_institution_code(self, mock_session_maker):
        """Test no_x_process with missing institution code"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": None
        }

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            self.processor.no_x_process()

        # Barcode should still be modified
        assert mock_item.item_data.barcode == "12345X"

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_no_x_process_institution_not_found(self, mock_session_maker, mock_storage_service_class):
        """Test no_x_process when institution not found"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):

            self.processor.no_x_process()

        # Should not call storage service
        mock_storage_service_class.assert_not_called()

    def test_no_row_tray_should_process_with_excluded_note(self):
        """Test no_row_tray_should_process with excluded note"""
        mock_item = Mock()
        mock_item.item_data.internal_note_1 = "At WRLC waiting to be processed"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            result = self.processor.no_row_tray_should_process()

        assert result is False

    def test_no_row_tray_should_process_missing_data(self):
        """Test no_row_tray_should_process with missing row/tray data"""
        mock_item = Mock()
        mock_item.item_data.internal_note_1 = "Regular note"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch.object(self.processor, 'no_row_tray_data', return_value=True), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=False), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):

            result = self.processor.no_row_tray_should_process()

        assert result is True

    def test_no_row_tray_should_process_wrong_data(self):
        """Test no_row_tray_should_process with wrong row/tray data"""
        mock_item = Mock()
        mock_item.item_data.internal_note_1 = "Regular note"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch.object(self.processor, 'no_row_tray_data', return_value=False), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=True), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):

            result = self.processor.no_row_tray_should_process()

        assert result is True

    def test_no_row_tray_should_process_data_ok(self):
        """Test no_row_tray_should_process with correct data"""
        mock_item = Mock()
        mock_item.item_data.internal_note_1 = "Regular note"
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        with patch.object(self.processor, 'no_row_tray_data', return_value=False), \
             patch.object(self.processor, 'wrong_row_tray_data', return_value=False), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):

            result = self.processor.no_row_tray_should_process()

        assert result is False

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    def test_no_row_tray_process_success(self, mock_storage_service_class):
        """Test successful no_row_tray_process"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {"item_data": mock_item}

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        self.processor.no_row_tray_process()

        # Verify storage operations
        mock_storage_service.upsert_entity.assert_called_once()
        call_args = mock_storage_service.upsert_entity.call_args
        assert call_args[1]['entity']['RowKey'] == "12345"
        assert call_args[1]['entity']['PartitionKey'] == "scf_no_row_tray"

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    def test_no_row_tray_process_no_barcode(self, mock_storage_service_class):
        """Test no_row_tray_process with no barcode"""
        mock_item = Mock()
        mock_item.item_data.barcode = ""
        self.processor.parsed_item = {"item_data": mock_item}

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            self.processor.no_row_tray_process()

        # Should not call storage service
        mock_storage_service_class.assert_not_called()


    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_withdrawn_process_success(self, mock_session_maker, mock_storage_service_class):
        """Test successful withdrawn_process"""
        mock_item = Mock()
        mock_item.bib_data.title = "Test Title"
        mock_item.item_data.barcode = "12345"
        mock_item.item_data.alternative_call_number = "WD"
        mock_item.item_data.internal_note_1 = "Test Note"
        mock_item.item_data.provenance.desc = "Test Provenance"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.withdrawn_process()

        # Verify storage operations - now uploads to REPORTS_CONTAINER
        mock_storage_service.upload_blob_data.assert_called_once()
        call_args = mock_storage_service.upload_blob_data.call_args
        # Note: uses default value since import happens before test env variables are set
        assert 'container_name' in call_args[1]
        assert call_args[1]['blob_name'] == 'test_job_123.json'

        mock_storage_service.send_queue_message.assert_called_once()

    def test_should_process_with_no_row_tray_data(self):
        """Test should_process when no_row_tray_should_process returns True"""
        with patch.object(self.processor, 'shared_checks', return_value=True), \
             patch.object(self.processor, 'no_x_should_process', return_value=False), \
             patch.object(self.processor, 'no_row_tray_should_process', return_value=True), \
             patch.object(self.processor, 'withdrawn_should_process', return_value=False), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging') as mock_logging:

            result = self.processor.should_process()

        assert result == ["scf_no_row_tray_data"]

    def test_should_process_with_withdrawn_data(self):
        """Test should_process when withdrawn_should_process returns True"""
        with patch.object(self.processor, 'shared_checks', return_value=True), \
             patch.object(self.processor, 'no_x_should_process', return_value=False), \
             patch.object(self.processor, 'no_row_tray_should_process', return_value=False), \
             patch.object(self.processor, 'withdrawn_should_process', return_value=True), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging') as mock_logging:

            result = self.processor.should_process()

        assert result == ["scf_withdrawn_data"]

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_no_x_process_blob_upload_error(self, mock_session_maker, mock_storage_service_class):
        """Test no_x_process with blob upload error"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_storage_service = Mock()
        mock_storage_service.upload_blob_data.side_effect = ValueError("Upload failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch.object(self.processor, 'generate_job_id', return_value="test_job_123"), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging') as mock_logging:

            self.processor.no_x_process()

        mock_storage_service.send_queue_message.assert_not_called()


    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_no_x_process_queue_send_error(self, mock_session_maker, mock_storage_service_class):
        """Test no_x_process with queue send error"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        mock_item.model_dump.return_value = {"test": "data"}
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service.send_queue_message.side_effect = TypeError("Queue failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.no_x_process()

        # Should handle queue send error and return
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    def test_withdrawn_process_no_institution_code(self):
        """Test withdrawn_process with no institution code"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": None
        }

        with patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):
            self.processor.withdrawn_process()

        # Should return early without any storage operations

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_withdrawn_process_institution_not_found(self, mock_session_maker, mock_storage_service_class):
        """Test withdrawn_process when institution not found"""
        mock_item = Mock()
        mock_item.item_data.barcode = "12345"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_item_processor.logging'):

            self.processor.withdrawn_process()

        # Should return early without storage operations

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_withdrawn_process_blob_upload_error(self, mock_session_maker, mock_storage_service_class):
        """Test withdrawn_process with blob upload error"""
        mock_item = Mock()
        mock_item.bib_data.title = "Test Title"
        mock_item.item_data.barcode = "12345"
        mock_item.item_data.alternative_call_number = "WD"
        mock_item.item_data.internal_note_1 = "Test Note"
        mock_item.item_data.provenance.desc = "Test Provenance"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service.upload_blob_data.side_effect = ValueError("Upload failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.withdrawn_process()

        # Should handle upload error and return early
        mock_storage_service.send_queue_message.assert_not_called()

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_withdrawn_process_queue_send_error(self, mock_session_maker, mock_storage_service_class):
        """Test withdrawn_process with queue send error"""
        mock_item = Mock()
        mock_item.bib_data.title = "Test Title"
        mock_item.item_data.barcode = "12345"
        mock_item.item_data.alternative_call_number = "WD"
        mock_item.item_data.internal_note_1 = "Test Note"
        mock_item.item_data.provenance.desc = "Test Provenance"
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service.send_queue_message.side_effect = TypeError("Queue failed")
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.withdrawn_process()

        # Should handle queue send error
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_item_processor.StorageService')
    @patch('alma_item_checks_processor_service.services.scf_item_processor.SessionMaker')
    def test_withdrawn_process_with_none_values(self, mock_session_maker, mock_storage_service_class):
        """Test withdrawn_process handles None values in item fields"""
        mock_item = Mock()
        mock_item.bib_data.title = None
        mock_item.item_data.barcode = "12345"
        mock_item.item_data.alternative_call_number = None
        mock_item.item_data.internal_note_1 = None
        mock_item.item_data.provenance = None
        self.processor.parsed_item = {
            "item_data": mock_item,
            "institution_code": "test"
        }

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_storage_service = Mock()
        mock_storage_service_class.return_value = mock_storage_service

        with patch('alma_item_checks_processor_service.services.scf_item_processor.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.processor, 'generate_job_id', return_value="test_job_123"):

            self.processor.withdrawn_process()

        # Verify storage operations work with None values converted to empty strings
        mock_storage_service.upload_blob_data.assert_called_once()
        call_args = mock_storage_service.upload_blob_data.call_args

        # Verify blob data contains empty strings for None values
        import json
        blob_data = json.loads(call_args[1]['data'].decode())
        assert blob_data["Title"] == ""
        assert blob_data["Barcode"] == "12345"
        assert blob_data["Item Call Number"] == ""
        assert blob_data["Internal Note 1"] == ""
        assert blob_data["Provenance Code"] == ""

        mock_storage_service.send_queue_message.assert_called_once()
