"""Tests for services/processor_service.py"""

from unittest.mock import Mock, patch
import pytest
from alma_item_checks_processor_service.services.processor_service import ProcessorService


class TestProcessorService:
    """Test cases for ProcessorService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_queue_message = Mock()
        self.service = ProcessorService(self.mock_queue_message)

    def test_init(self):
        """Test ProcessorService initialization"""
        assert self.service.barcodemsg == self.mock_queue_message

    def test_get_item_by_barcode_success(self):
        """Test successful item retrieval by barcode"""
        mock_barcode_data = {'institution_code': 'test', 'barcode': '123'}
        mock_institution = Mock()
        mock_institution.code = 'test'
        mock_item = Mock()

        with patch.object(self.service, 'get_barcode_retrieval_data', return_value=mock_barcode_data), \
             patch.object(self.service, 'get_institution', return_value=mock_institution), \
             patch('alma_item_checks_processor_service.services.processor_service.BaseItemProcessor') as mock_base_processor:
            mock_base_processor.retrieve_item_by_barcode.return_value = mock_item

            result = self.service.get_item_by_barcode()

            assert result['institution_code'] == 'test'
            assert result['item_data'] == mock_item

    def test_get_item_by_barcode_no_data(self):
        """Test get_item_by_barcode with no barcode retrieval data"""
        with patch.object(self.service, 'get_barcode_retrieval_data', return_value=None):
            result = self.service.get_item_by_barcode()
            assert result is None

    def test_get_item_by_barcode_no_institution(self):
        """Test get_item_by_barcode with no institution"""
        mock_barcode_data = {'institution_code': 'test', 'barcode': '123'}
        with patch.object(self.service, 'get_barcode_retrieval_data', return_value=mock_barcode_data), \
             patch.object(self.service, 'get_institution', return_value=None):
            result = self.service.get_item_by_barcode()
            assert result is None

    @patch('alma_item_checks_processor_service.services.processor_service.SCFItemProcessor')
    def test_should_process_scf(self, mock_scf_processor):
        """Test should_process for SCF institution"""
        parsed_item = {'institution_code': 'scf'}
        mock_scf_processor.return_value.should_process.return_value = ['scf_no_row_tray']

        result = self.service.should_process(parsed_item)

        assert result == ['scf_no_row_tray']

    @patch('alma_item_checks_processor_service.services.processor_service.IZItemProcessor')
    def test_should_process_iz(self, mock_iz_processor):
        """Test should_process for IZ institution"""
        parsed_item = {'institution_code': 'iz'}
        mock_iz_processor.return_value.should_process.return_value = ['iz_no_row_tray']

        result = self.service.should_process(parsed_item)

        assert result == ['iz_no_row_tray']

    def test_should_process_no_institution(self):
        """Test should_process with no institution"""
        parsed_item = {'institution_code': None}

        result = self.service.should_process(parsed_item)

        assert result is None

    @patch('alma_item_checks_processor_service.services.processor_service.SCFItemProcessor')
    def test_process_scf(self, mock_scf_processor):
        """Test process for SCF institution"""
        parsed_item = {'institution_code': 'scf'}
        processes = ['scf_no_row_tray']

        self.service.process(parsed_item, processes)

        mock_scf_processor.return_value.process.assert_called_once_with(processes)

    @patch('alma_item_checks_processor_service.services.processor_service.IZItemProcessor')
    def test_process_iz(self, mock_iz_processor):
        """Test process for IZ institution"""
        parsed_item = {'institution_code': 'iz'}
        processes = ['iz_no_row_tray']

        self.service.process(parsed_item, processes)

        mock_iz_processor.return_value.process.assert_called_once_with(processes)

    def test_process_no_institution(self):
        """Test process with no institution"""
        parsed_item = {'institution_code': None}
        processes = ['iz_no_row_tray']

        self.service.process(parsed_item, processes)

    def test_get_barcode_retrieval_data_success(self):
        """Test successful parsing of barcode retrieval data"""
        message_body = b'{"institution": "test", "barcode": "123"}'
        self.mock_queue_message.get_body.return_value = message_body

        result = self.service.get_barcode_retrieval_data()

        assert result == {'institution_code': 'test', 'barcode': '123'}

    def test_get_barcode_retrieval_data_missing_institution(self):
        """Test get_barcode_retrieval_data with missing institution"""
        message_body = b'{"barcode": "123"}'
        self.mock_queue_message.get_body.return_value = message_body

        result = self.service.get_barcode_retrieval_data()

        assert result is None

    @patch('alma_item_checks_processor_service.services.processor_service.SessionMaker')
    def test_get_institution_success(self, mock_session_maker):
        """Test successful institution retrieval"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session
        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = Mock()

        with patch('alma_item_checks_processor_service.services.processor_service.InstitutionService', return_value=mock_institution_service):
            self.service.get_institution('test')

        mock_institution_service.get_institution_by_code.assert_called_once_with(code='test')

    def test_get_item_by_barcode_exception(self):
        """Test exception handling in get_item_by_barcode"""
        with patch.object(self.service, 'get_barcode_retrieval_data', side_effect=Exception('Test')):
            with pytest.raises(Exception):
                self.service.get_item_by_barcode()

    def test_should_process_exception(self):
        """Test exception handling in should_process"""
        with patch('alma_item_checks_processor_service.services.processor_service.SCFItemProcessor', side_effect=Exception('Test')):
            with pytest.raises(Exception):
                self.service.should_process({'institution_code': 'scf'})

    def test_process_exception(self):
        """Test exception handling in process"""
        with patch('alma_item_checks_processor_service.services.processor_service.SCFItemProcessor', side_effect=Exception('Test')):
            with pytest.raises(Exception):
                self.service.process({'institution_code': 'scf'}, ['scf_no_row_tray'])

    def test_get_barcode_retrieval_data_missing_barcode(self):
        """Test get_barcode_retrieval_data with missing barcode"""
        message_body = b'{"institution": "test"}'
        self.mock_queue_message.get_body.return_value = message_body

        result = self.service.get_barcode_retrieval_data()

        assert result is None
