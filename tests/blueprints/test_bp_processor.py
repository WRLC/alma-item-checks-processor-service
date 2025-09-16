"""Tests for blueprints/bp_processor.py"""

import json
import pytest
from unittest.mock import Mock, patch
import azure.functions as func
from alma_item_checks_processor_service.blueprints.bp_processor import process_item_data


class TestBpProcessor:
    """Test cases for bp_processor blueprint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_message = Mock(spec=func.QueueMessage)
        self.mock_message.get_body.return_value.decode.return_value = json.dumps({
            "institution": "test",
            "barcode": "12345"
        })

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_success(self, mock_processor_service_class):
        """Test successful item data processing"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        mock_parsed_item = {"institution_code": "test", "item_data": Mock()}
        mock_service.get_item_by_barcode.return_value = mock_parsed_item
        mock_service.should_process.return_value = ["scf_no_x"]

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logging'):
            process_item_data(self.mock_message)

        # Verify the service methods were called
        mock_service.get_item_by_barcode.assert_called_once()
        mock_service.should_process.assert_called_once_with(mock_parsed_item)
        mock_service.process.assert_called_once_with(mock_parsed_item, ["scf_no_x"])

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_no_item_data(self, mock_processor_service_class):
        """Test processing when no item data returned"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        mock_service.get_item_by_barcode.return_value = None

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logging'):
            process_item_data(self.mock_message)

        # Should not call should_process or process when no item data
        mock_service.get_item_by_barcode.assert_called_once()
        mock_service.should_process.assert_not_called()
        mock_service.process.assert_not_called()

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_no_processing_needed(self, mock_processor_service_class):
        """Test processing when no processing is needed"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        mock_parsed_item = {"institution_code": "test", "item_data": Mock()}
        mock_service.get_item_by_barcode.return_value = mock_parsed_item
        mock_service.should_process.return_value = None

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logging'):
            process_item_data(self.mock_message)

        # Should not call process when no processing needed
        mock_service.get_item_by_barcode.assert_called_once()
        mock_service.should_process.assert_called_once_with(mock_parsed_item)
        mock_service.process.assert_not_called()

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_empty_processing_list(self, mock_processor_service_class):
        """Test processing when empty processing list returned"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        mock_parsed_item = {"institution_code": "test", "item_data": Mock()}
        mock_service.get_item_by_barcode.return_value = mock_parsed_item
        mock_service.should_process.return_value = []

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logging'):
            process_item_data(self.mock_message)

        # Should not call process when empty list returned
        mock_service.get_item_by_barcode.assert_called_once()
        mock_service.should_process.assert_called_once_with(mock_parsed_item)
        mock_service.process.assert_not_called()

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_exception_handling(self, mock_processor_service_class):
        """Test exception handling in process_item_data"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        # Make get_item_by_barcode raise an exception
        mock_service.get_item_by_barcode.side_effect = Exception("Test error")

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logger') as mock_logger:
            # Exception should be logged and re-raised
            with pytest.raises(Exception, match="Test error"):
                process_item_data(self.mock_message)

            # Verify error was logged
            mock_logger.error.assert_called()

    @patch('alma_item_checks_processor_service.blueprints.bp_processor.ProcessorService')
    def test_process_item_data_with_logging(self, mock_processor_service_class):
        """Test that logging statements are called appropriately"""
        mock_service = Mock()
        mock_processor_service_class.return_value = mock_service

        mock_parsed_item = {"institution_code": "test", "item_data": Mock()}
        mock_service.get_item_by_barcode.return_value = mock_parsed_item
        mock_service.should_process.return_value = ["scf_no_x"]

        with patch('alma_item_checks_processor_service.blueprints.bp_processor.logger') as mock_logger:
            process_item_data(self.mock_message)

        # Verify logging calls were made
        assert mock_logger.info.call_count >= 1
