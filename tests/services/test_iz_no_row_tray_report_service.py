"""Tests for services/iz_no_row_tray_report_service.py"""

import pytest
from unittest.mock import Mock, patch
from alma_item_checks_processor_service.services.iz_no_row_tray_report_service import IZNoRowTrayReportService


class TestIZNoRowTrayReportService:
    """Test cases for IZNoRowTrayReportService"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.StorageService'):
            self.service = IZNoRowTrayReportService()

    def test_init(self):
        """Test IZNoRowTrayReportService initialization"""
        assert hasattr(self.service, 'storage_service')

    def test_get_staged_items_success(self):
        """Test successful staged items retrieval"""
        mock_entities = [{"PartitionKey": "iz_no_row_tray", "RowKey": "12345", "institution_code": "doc"}]
        self.service.storage_service.get_entities.return_value = mock_entities

        result = self.service._get_staged_items()

        assert result == mock_entities
        self.service.storage_service.get_entities.assert_called_once()

    def test_get_staged_items_error(self):
        """Test staged items retrieval with error"""
        self.service.storage_service.get_entities.side_effect = Exception("Storage error")

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):
            result = self.service._get_staged_items()

        assert result == []

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_single_item_institution_not_found(self, mock_session_maker):
        """Test _process_single_item when institution not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service):
            result = self.service._process_single_item("12345", "doc")

        expected = {
            "success": False,
            "reason": "Institution doc not found in database"
        }
        assert result == expected

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_single_item_item_not_found(self, mock_session_maker):
        """Test _process_single_item when item not found in Alma"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.BaseItemProcessor.retrieve_item_by_barcode',
                   return_value=None):

            result = self.service._process_single_item("12345", "doc")

        assert result == {"success": False, "reason": "Item not found in Alma"}

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_single_item_no_longer_meets_criteria(self, mock_session_maker):
        """Test _process_single_item when item no longer meets processing criteria"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_item = Mock()
        mock_processor = Mock()
        mock_processor.no_row_tray_should_process.return_value = False

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.BaseItemProcessor.retrieve_item_by_barcode',
                   return_value=mock_item), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.IZItemProcessor',
                   return_value=mock_processor):

            result = self.service._process_single_item("12345", "doc")

        assert result == {"success": False, "reason": "No longer meets processing criteria"}

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_single_item_update_failed(self, mock_session_maker):
        """Test _process_single_item when update fails"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_item = Mock()
        mock_processor = Mock()
        mock_processor.no_row_tray_should_process.return_value = True
        mock_processor.no_row_tray_report_process.return_value = False

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.BaseItemProcessor.retrieve_item_by_barcode',
                   return_value=mock_item), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.IZItemProcessor',
                   return_value=mock_processor):

            result = self.service._process_single_item("12345", "doc")

        assert result == {"success": False, "reason": "Failed to update item with SCF data"}

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_single_item_success(self, mock_session_maker):
        """Test successful _process_single_item"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_item = Mock()
        mock_processor = Mock()
        mock_processor.no_row_tray_should_process.return_value = True
        mock_processor.no_row_tray_report_process.return_value = True

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.BaseItemProcessor.retrieve_item_by_barcode',
                   return_value=mock_item), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.IZItemProcessor',
                   return_value=mock_processor):

            result = self.service._process_single_item("12345", "doc")

        assert result == {"success": True}

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.uuid')
    def test_create_batch_job(self, mock_uuid):
        """Test _create_batch_job method"""
        mock_uuid.uuid4.return_value = 'test-job-id'

        result = self.service._create_batch_job(50)

        assert result == 'test-job-id'

    def test_enqueue_batches(self):
        """Test _enqueue_batches method"""
        staged_entities = [
            {'RowKey': '123', 'institution_code': 'doc'},
            {'RowKey': '456', 'institution_code': 'gw'},
            {'RowKey': '789', 'institution_code': 'doc'}
        ]

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.IZ_NO_ROW_TRAY_BATCH_SIZE', 2):
            self.service._enqueue_batches(staged_entities, 'job-id-123')

        # Should create 2 batches (2 items + 1 item)
        assert self.service.storage_service.send_queue_message.call_count == 2

    def test_process_batch(self):
        """Test process_batch method"""
        items = [
            {'barcode': '123', 'institution_code': 'doc'},
            {'barcode': '456', 'institution_code': 'gw'}
        ]

        with patch.object(self.service, '_process_single_item', side_effect=[{'success': True}, {'success': False, 'reason': 'Failed'}]), \
             patch.object(self.service, '_clear_batch_from_staging'):

            self.service.process_batch('job-id-123', 1, items)

            assert self.service._process_single_item.call_count == 2
            self.service._clear_batch_from_staging.assert_called_once_with(items)

    def test_process_staged_items_report_no_staged_items(self):
        """Test process_staged_items_report when no staged items"""
        with patch.object(self.service, '_get_staged_items', return_value=[]), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):

            # Should return early without errors
            self.service.process_staged_items_report()

    def test_clear_batch_from_staging(self):
        """Test _clear_batch_from_staging method"""
        items = [
            {'barcode': '123', 'institution_code': 'doc'},
            {'barcode': '456', 'institution_code': 'gw'}
        ]

        self.service._clear_batch_from_staging(items)

        assert self.service.storage_service.delete_entity.call_count == 2

    def test_process_staged_items_report_with_items(self):
        """Test process_staged_items_report when items are found - batch processing"""
        mock_staged_entities = [{'RowKey': '123', 'institution_code': 'doc'}]

        with patch.object(self.service, '_get_staged_items', return_value=mock_staged_entities), \
             patch.object(self.service, '_create_batch_job', return_value='job-id-123'), \
             patch.object(self.service, '_enqueue_batches'):
            self.service.process_staged_items_report()

            self.service._get_staged_items.assert_called_once()
            self.service._create_batch_job.assert_called_once_with(1)
            self.service._enqueue_batches.assert_called_once_with(mock_staged_entities, 'job-id-123')
