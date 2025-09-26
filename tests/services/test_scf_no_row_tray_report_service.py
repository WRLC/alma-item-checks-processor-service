"""Tests for services/scf_no_row_tray_report_service.py"""

import pytest
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
        """Test successful processing of staged items report with batch processing"""
        mock_institution = Mock()
        mock_staged_entities = [{'RowKey': '123'}]

        with patch.object(self.service, '_get_scf_institution', return_value=mock_institution), \
             patch.object(self.service, '_get_staged_items', return_value=mock_staged_entities), \
             patch.object(self.service, '_create_batch_job', return_value='job-id-123'), \
             patch.object(self.service, '_enqueue_batches'):
            self.service.process_staged_items_report()

            self.service._get_scf_institution.assert_called_once()
            self.service._get_staged_items.assert_called_once()
            self.service._create_batch_job.assert_called_once_with(1)
            self.service._enqueue_batches.assert_called_once_with(mock_staged_entities, 'job-id-123')

    def test_process_staged_items_report_job_already_running(self):
        """Test process_staged_items_report skips when job is already running"""
        with patch.object(self.service, '_is_job_already_running', return_value=True):
            self.service.process_staged_items_report()
            # Should not call any other methods

    def test_is_job_already_running_no_jobs(self):
        """Test _is_job_already_running when no jobs are running"""
        self.service.storage_service.get_entities.return_value = []

        result = self.service._is_job_already_running()

        assert result is False

    def test_is_job_already_running_has_jobs(self):
        """Test _is_job_already_running when jobs are in progress"""
        self.service.storage_service.get_entities.return_value = [{'status': 'in_progress'}]

        result = self.service._is_job_already_running()

        assert result is True

    def test_is_job_already_running_exception(self):
        """Test _is_job_already_running handles exceptions gracefully"""
        self.service.storage_service.get_entities.side_effect = Exception("Storage error")

        result = self.service._is_job_already_running()

        assert result is False  # Should not block on error

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

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.uuid')
    def test_create_batch_job(self, mock_uuid):
        """Test _create_batch_job method"""
        mock_uuid.uuid4.return_value = 'test-job-id'

        result = self.service._create_batch_job(50)

        assert result == 'test-job-id'
        self.service.storage_service.upsert_entity.assert_called_once()

    def test_enqueue_batches(self):
        """Test _enqueue_batches method"""
        staged_entities = [
            {'RowKey': '123'},
            {'RowKey': '456'},
            {'RowKey': '789'}
        ]

        with patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.SCF_NO_ROW_TRAY_BATCH_SIZE', 2):
            self.service._enqueue_batches(staged_entities, 'job-id-123')

        # Should create 2 batches (2 items + 1 item)
        assert self.service.storage_service.send_queue_message.call_count == 2

    def test_process_batch(self):
        """Test process_batch method"""
        barcodes = ['123', '456']

        with patch.object(self.service, '_get_scf_institution', return_value=Mock()), \
             patch.object(self.service, '_process_single_item', side_effect=[{'success': True}, {'success': False, 'reason': 'Failed'}]), \
             patch.object(self.service, '_update_batch_progress'), \
             patch.object(self.service, '_clear_batch_from_staging'):

            self.service.process_batch('job-id-123', 1, barcodes)

            assert self.service._process_single_item.call_count == 2
            self.service._update_batch_progress.assert_called_once_with('job-id-123', 1, 1)
            self.service._clear_batch_from_staging.assert_called_once_with(barcodes)

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

    def test_clear_batch_from_staging(self):
        """Test _clear_batch_from_staging method"""
        barcodes = ['123', '456']

        self.service._clear_batch_from_staging(barcodes)

        assert self.service.storage_service.delete_entity.call_count == 2

    def test_update_batch_progress(self):
        """Test _update_batch_progress method"""
        mock_job_entity = {
            'completed_batches': 1,
            'processed_items': 5,
            'failed_items': 1,
            'total_batches': 3
        }
        self.service.storage_service.get_entities.return_value = [mock_job_entity]

        self.service._update_batch_progress('job-id-123', 3, 1)

        self.service.storage_service.upsert_entity.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_no_row_tray_report_service.datetime')
    def test_generate_final_report(self, mock_datetime):
        """Test _generate_final_report method"""
        mock_now = Mock()
        mock_now.strftime.return_value = '20250101_120000'
        mock_now.isoformat.return_value = '2025-01-01T12:00:00+00:00'
        mock_datetime.now.return_value = mock_now
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')

        job_entity = {
            'RowKey': 'job-id-123',
            'total_items': 10,
            'total_batches': 2,
            'processed_items': 8,
            'failed_items': 2,
            'created_at': '2025-01-01T11:00:00+00:00',
            'completed_at': '2025-01-01T12:00:00+00:00'
        }

        with patch.object(self.service, '_send_notification') as mock_send_notification:
            self.service._generate_final_report(job_entity)

        self.service.storage_service.upload_blob_data.assert_called_once()
        mock_send_notification.assert_called_once()

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

    def test_create_batch_job_exception(self):
        """Test _create_batch_job when storage operation fails"""
        self.service.storage_service.upsert_entity.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            self.service._create_batch_job(50)

    def test_get_processed_items_for_job_exception(self):
        """Test _get_processed_items_for_job when storage operation fails"""
        self.service.storage_service.get_entities.side_effect = Exception("Storage error")

        result = self.service._get_processed_items_for_job("job-id", "processed_item")

        assert result == []

    def test_update_batch_progress_job_not_found(self):
        """Test _update_batch_progress when job entity is not found"""
        self.service.storage_service.get_entities.return_value = []

        self.service._update_batch_progress('job-id-123', 1, 0)

        # Should not call upsert if job not found
        self.service.storage_service.upsert_entity.assert_not_called()

    def test_update_batch_progress_exception(self):
        """Test _update_batch_progress when storage operation fails"""
        self.service.storage_service.get_entities.side_effect = Exception("Storage error")

        self.service._update_batch_progress('job-id-123', 1, 0)

        # Should handle exception gracefully
        self.service.storage_service.upsert_entity.assert_not_called()

    def test_generate_final_report_upload_exception(self):
        """Test _generate_final_report when upload fails"""
        self.service.scf_institution = Institution(id=1, code='scf', name='SCF')
        self.service.storage_service.upload_blob_data.side_effect = Exception("Upload error")

        job_entity = {
            'RowKey': 'job-id-123',
            'total_items': 10,
            'total_batches': 2,
            'created_at': '2025-01-01T11:00:00+00:00',
            'completed_at': '2025-01-01T12:00:00+00:00'
        }

        with patch.object(self.service, '_get_processed_items_for_job', return_value=[]), \
             patch.object(self.service, '_send_notification') as mock_send:

            self.service._generate_final_report(job_entity)

            # Should not call send_notification if upload fails
            mock_send.assert_not_called()

    def test_clear_batch_from_staging_exception(self):
        """Test _clear_batch_from_staging when delete operation fails"""
        self.service.storage_service.delete_entity.side_effect = Exception("Delete error")

        barcodes = ['123', '456']
        self.service._clear_batch_from_staging(barcodes)

        # Should attempt to delete all items even if some fail
        assert self.service.storage_service.delete_entity.call_count == 2
