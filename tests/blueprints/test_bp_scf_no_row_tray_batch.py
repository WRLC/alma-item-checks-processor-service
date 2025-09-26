"""Tests for bp_scf_no_row_tray_batch.py"""

import json
from unittest.mock import Mock, patch
import azure.functions as func

from alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray_batch import process_scf_no_row_tray_batch


class TestSCFNoRowTrayBatchBlueprint:
    """Test cases for SCF no row tray batch blueprint"""

    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray_batch.SCFNoRowTrayReportService')
    def test_process_scf_no_row_tray_batch_success(self, mock_service_class):
        """Test successful processing of SCF batch"""
        # Mock the queue message
        message_body = json.dumps({
            "job_id": "test-job-id",
            "batch_number": 1,
            "barcodes": ["123", "456"]
        })
        mock_msg = Mock(spec=func.QueueMessage)
        mock_msg.get_body.return_value = message_body.encode('utf-8')

        # Mock the service
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Call the function
        process_scf_no_row_tray_batch(mock_msg)

        # Verify service was called correctly
        mock_service_class.assert_called_once()
        mock_service.process_batch.assert_called_once_with("test-job-id", 1, ["123", "456"])

    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray_batch.SCFNoRowTrayReportService')
    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray_batch.logging')
    def test_process_scf_no_row_tray_batch_exception(self, mock_logging, mock_service_class):
        """Test handling of exceptions during batch processing"""
        # Mock the queue message
        message_body = json.dumps({
            "job_id": "test-job-id",
            "batch_number": 1,
            "barcodes": ["123", "456"]
        })
        mock_msg = Mock(spec=func.QueueMessage)
        mock_msg.get_body.return_value = message_body.encode('utf-8')

        # Mock the service to raise an exception
        mock_service = Mock()
        mock_service.process_batch.side_effect = Exception("Processing failed")
        mock_service_class.return_value = mock_service

        # Call the function and expect it to raise
        try:
            process_scf_no_row_tray_batch(mock_msg)
            assert False, "Expected exception to be raised"
        except Exception as e:
            assert str(e) == "Processing failed"

        # Verify error was logged
        mock_logging.error.assert_called_once()

    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray_batch.SCFNoRowTrayReportService')
    def test_process_scf_no_row_tray_batch_invalid_json(self, mock_service_class):
        """Test handling of invalid JSON in queue message"""
        # Mock the queue message with invalid JSON
        mock_msg = Mock(spec=func.QueueMessage)
        mock_msg.get_body.return_value = b"invalid json"

        # Call the function and expect it to raise
        try:
            process_scf_no_row_tray_batch(mock_msg)
            assert False, "Expected exception to be raised"
        except json.JSONDecodeError:
            pass  # Expected

        # Service should not be called
        mock_service_class.assert_not_called()
