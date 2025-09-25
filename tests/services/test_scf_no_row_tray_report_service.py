"""Tests for services/scf_no_row_tray_report_service.py"""

from unittest.mock import Mock, patch
from alma_item_checks_processor_service.services.scf_no_row_tray_report_service import SCFNoRowTrayReportService
from alma_item_checks_processor_service.models import Institution
from alma_item_checks_processor_service.config import SCF_INSTITUTION_CODE


class TestSCFNoRowTrayReportService:
    """Test cases for SCFNoRowTrayReportService"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.StorageService'), \
             patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SessionMaker'), \
             patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.logging'):
            self.service = SCFNoRowTrayReportService()

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SessionMaker')
    def test_get_scf_institution_fallback(self, mock_session_maker):
        """Test _get_scf_institution"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.side_effect = [None, Mock()]

        with patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service):
            self.service._get_scf_institution()

        assert mock_institution_service.get_institution_by_code.call_count == 1
        mock_institution_service.get_institution_by_code.assert_any_call(SCF_INSTITUTION_CODE)

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SessionMaker')
    def test_get_scf_institution_success(self, mock_session_maker):
        """Test _get_scf_institution with success"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = Mock()

        with patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service):
            self.service._get_scf_institution()

        mock_institution_service.get_institution_by_code.assert_called_once_with(SCF_INSTITUTION_CODE)

    def test_process_staged_items_report_no_institution(self):
        """Test process_staged_items_report when no SCF institution is found"""
        with patch.object(self.service, '_get_scf_institution', return_value=None):
            self.service.process_staged_items_report()
            # Add assertions to check logging and early return

    def test_process_staged_items_report_no_staged_items(self):
        """Test process_staged_items_report when no staged items are found"""
        with patch.object(self.service, '_get_scf_institution', return_value=Mock()), \
             patch.object(self.service, '_get_staged_items', return_value=[]):
            self.service.process_staged_items_report()
            # Add assertions to check logging and early return

    def test_process_staged_items_report_success(self):
        """Test successful processing of staged items report"""
        mock_institution = Mock()
        mock_staged_entities = [{'RowKey': '123'}]
        mock_processed_items = [{'barcode': '123'}]
        mock_failed_items = []

        with patch.object(self.service, '_get_scf_institution', return_value=mock_institution), \
             patch.object(self.service, '_get_staged_items', return_value=mock_staged_entities), \
             patch.object(self.service, '_process_staged_items', return_value=(mock_processed_items, mock_failed_items)), \
             patch.object(self.service, '_clear_staging_table'), \
             patch.object(self.service, '_generate_report', return_value='report_blob_name'), \
             patch.object(self.service, '_send_notification'):
            self.service.process_staged_items_report()

            self.service._get_scf_institution.assert_called_once()
            self.service._get_staged_items.assert_called_once()
            self.service._process_staged_items.assert_called_once_with(mock_staged_entities)
            self.service._clear_staging_table.assert_called_once_with(mock_staged_entities)
            self.service._generate_report.assert_called_once_with(1, mock_processed_items, mock_failed_items)
            self.service._send_notification.assert_called_once_with('report_blob_name')

    def test_get_staged_items_success(self):
        """Test _get_staged_items successfully retrieves entities"""
        mock_entities = [{'RowKey': '123'}]
        self.service.storage_service.get_entities.return_value = mock_entities

        result = self.service._get_staged_items()

        assert result == mock_entities
        self.service.storage_service.get_entities.assert_called_once_with(
            table_name='scfnorowtraystagetable',
            filter_query="PartitionKey eq 'scf_no_row_tray'",
        )

    def test_get_staged_items_exception(self):
        """Test _get_staged_items handles exceptions"""
        self.service.storage_service.get_entities.side_effect = Exception("Test Exception")

        result = self.service._get_staged_items()

        assert result == []

    def test_process_staged_items(self):
        """Test _process_staged_items method"""
        staged_entities = [{'RowKey': '123'}, {'RowKey': '456'}, {'RowKey': None}]

        with patch.object(self.service, '_process_single_item', side_effect=[{'success': True}, {'success': False, 'reason': 'Failed'}]):
            processed, failed = self.service._process_staged_items(staged_entities)

            assert len(processed) == 1
            assert len(failed) == 1
            assert processed[0]['barcode'] == '123'
            assert failed[0]['barcode'] == '456'
            assert self.service._process_single_item.call_count == 2

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.BaseItemProcessor')
    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SCFItemProcessor')
    def test_process_single_item_success(self, mock_scf_item_processor, mock_base_item_processor):
        """Test _process_single_item successfully processes an item"""
        self.service.scf_institution = Mock()
        mock_item = Mock()
        mock_base_item_processor.retrieve_item_by_barcode.return_value = mock_item
        mock_processor_instance = mock_scf_item_processor.return_value
        mock_processor_instance.no_row_tray_should_process.return_value = True

        result = self.service._process_single_item('123')

        assert result['success'] is True

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.BaseItemProcessor')
    def test_process_single_item_not_found(self, mock_base_item_processor):
        """Test _process_single_item when item is not found in Alma"""
        self.service.scf_institution = Mock()
        mock_base_item_processor.retrieve_item_by_barcode.return_value = None

        result = self.service._process_single_item('123')

        assert result['success'] is False
        assert result['reason'] == 'Item not found in Alma'

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.BaseItemProcessor')
    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SCFItemProcessor')
    def test_process_single_item_no_longer_meets_criteria(self, mock_scf_item_processor, mock_base_item_processor):
        """Test _process_single_item when item no longer meets processing criteria"""
        self.service.scf_institution = Mock()
        mock_item = Mock()
        mock_base_item_processor.retrieve_item_by_barcode.return_value = mock_item
        mock_processor_instance = mock_scf_item_processor.return_value
        mock_processor_instance.no_row_tray_should_process.return_value = False

        result = self.service._process_single_item('123')

        assert result['success'] is False
        assert result['reason'] == 'No longer meets processing criteria'


    def test_process_single_item_no_institution(self):
        """Test _process_single_item when scf_institution is None"""
        self.service.scf_institution = None

        result = self.service._process_single_item('123')

        assert result == {}

    def test_clear_staging_table(self):
        """Test _clear_staging_table method"""
        staged_entities = [{'RowKey': '123'}, {'RowKey': '456'}, {'RowKey': None}]

        self.service._clear_staging_table(staged_entities)

        assert self.service.storage_service.delete_entity.call_count == 2

    def test_clear_staging_table_exception(self):
        """Test _clear_staging_table method when deleting an entity fails"""
        staged_entities = [{'RowKey': '123'}]
        self.service.storage_service.delete_entity.side_effect = Exception("Test Exception")

        self.service._clear_staging_table(staged_entities)

        self.service.storage_service.delete_entity.assert_called_once_with(
            table_name='scfnorowtraystagetable',
            partition_key='scf_no_row_tray',
            row_key='123'
        )

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.datetime')
    def test_generate_report(self, mock_datetime):
        """Test _generate_report method"""
        mock_now = Mock()
        mock_now.strftime.return_value = '20250101_120000'
        mock_now.isoformat.return_value = '2025-01-01T12:00:00+00:00'
        mock_datetime.now.return_value = mock_now
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')

        job_id = self.service._generate_report(1, [], [])

        assert job_id == 'scf_no_row_tray_report_20250101_120000'
        self.service.storage_service.upload_blob_data.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.datetime')
    def test_generate_report_exception(self, mock_datetime):
        """Test _generate_report method when storing the report fails"""
        mock_now = Mock()
        mock_now.strftime.return_value = '20250101_120000'
        mock_now.isoformat.return_value = '2025-01-01T12:00:00+00:00'
        mock_datetime.now.return_value = mock_now
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')
        self.service.storage_service.upload_blob_data.side_effect = Exception("Test Exception")

        job_id = self.service._generate_report(1, [], [])

        assert job_id is None

    def test_send_notification(self):
        """Test _send_notification method"""
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')

        self.service._send_notification('job_id')

        self.service.storage_service.send_queue_message.assert_called_once()

    def test_send_notification_exception(self):
        """Test _send_notification method when sending the notification fails"""
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')
        self.service.storage_service.send_queue_message.side_effect = Exception("Test Exception")

        self.service._send_notification('job_id')

        self.service.storage_service.send_queue_message.assert_called_once()

    def test_send_notification_no_institution(self):
        """Test _send_notification method when scf_institution is None"""
        self.service.scf_institution = None

        self.service._send_notification('job_id')

        self.service.storage_service.send_queue_message.assert_not_called()
