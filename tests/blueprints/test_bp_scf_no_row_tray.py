"""Tests for blueprints/bp_scf_no_row_tray.py"""

import pytest
from unittest.mock import Mock, patch
import azure.functions as func
from alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray import process_scf_no_row_tray_report


class TestBpScfNoRowTray:
    """Test cases for bp_scf_no_row_tray blueprint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_timer = Mock(spec=func.TimerRequest)

    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray.SCFNoRowTrayReportService')
    def test_process_scf_no_row_tray_report_success(self, mock_service_class):
        """Test successful SCF no row tray report processing"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        process_scf_no_row_tray_report(self.mock_timer)

        # Verify service was created and method called
        mock_service_class.assert_called_once()
        mock_service.process_staged_items_report.assert_called_once()

    @patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray.SCFNoRowTrayReportService')
    def test_process_scf_no_row_tray_report_exception(self, mock_service_class):
        """Test SCF no row tray report processing with exception"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.process_staged_items_report.side_effect = Exception("Service error")

        # Exception should be raised since blueprint doesn't handle exceptions
        with pytest.raises(Exception, match="Service error"):
            process_scf_no_row_tray_report(self.mock_timer)

        # Verify service method was called
        mock_service.process_staged_items_report.assert_called_once()

    def test_process_scf_no_row_tray_report_timer_parameter(self):
        """Test that function accepts timer parameter correctly"""
        # Test function signature accepts TimerRequest
        with patch('alma_item_checks_processor_service.blueprints.bp_scf_no_row_tray.SCFNoRowTrayReportService'):
            # Should not raise exception about parameter types
            process_scf_no_row_tray_report(self.mock_timer)
