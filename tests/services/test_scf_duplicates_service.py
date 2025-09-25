"""Tests for services/scf_duplicates_service.py"""

import pytest
from unittest.mock import Mock, patch
from alma_item_checks_processor_service.services.scf_duplicates_service import ScfDuplicatesService


class TestScfDuplicatesService:
    """Test cases for ScfDuplicatesService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = ScfDuplicatesService()

    def test_init(self):
        """Test ScfDuplicatesService initialization"""
        assert isinstance(self.service, ScfDuplicatesService)

    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.SessionMaker')
    def test_process_scf_duplicates_report_no_institution(self, mock_session_maker):
        """Test process_scf_duplicates_report when institution not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution_service.get_institution_by_code.return_value = None

        with patch('alma_item_checks_processor_service.services.scf_duplicates_service.InstitutionService',
                   return_value=mock_institution_service):
            # Should return early without errors
            self.service.process_scf_duplicates_report()

        assert mock_institution_service.get_institution_by_code.call_count == 1
        mock_institution_service.get_institution_by_code.assert_any_call("01WRLC_SCF")

    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.SessionMaker')
    def test_process_scf_duplicates_report_with_institution(self, mock_session_maker):
        """Test process_scf_duplicates_report with valid institution"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.duplicate_report_path = "/test/path"
        mock_institution.id = 1

        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_alma_client = Mock()
        mock_report = Mock()
        mock_report.rows = [{"test": "data"}]
        mock_alma_client.analytics.get_report.return_value = mock_report

        mock_storage_service = Mock()

        with patch('alma_item_checks_processor_service.services.scf_duplicates_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.AlmaApiClient',
                   return_value=mock_alma_client), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.StorageService',
                   return_value=mock_storage_service):

            self.service.process_scf_duplicates_report()

        mock_institution_service.get_institution_by_code.assert_called_once_with("01WRLC_SCF")
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.SessionMaker')
    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.datetime')
    def test_process_scf_duplicates_report_success(self, mock_datetime, mock_session_maker):
        """Test successful process_scf_duplicates_report"""
        mock_datetime.now.return_value.strftime.return_value = "20250916_120000"

        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.duplicate_report_path = "/test/path"
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_alma_client = Mock()
        mock_report = Mock()
        mock_report.rows = [{"test": "data"}]
        mock_alma_client.analytics.get_report.return_value = mock_report

        mock_storage_service = Mock()

        with patch('alma_item_checks_processor_service.services.scf_duplicates_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.AlmaApiClient',
                   return_value=mock_alma_client), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.StorageService',
                   return_value=mock_storage_service):

            self.service.process_scf_duplicates_report()

        mock_alma_client.analytics.get_report.assert_called_once_with("/test/path")
        mock_storage_service.upload_blob_data.assert_called_once()
        mock_storage_service.send_queue_message.assert_called_once()

    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.SessionMaker')
    def test_process_scf_duplicates_report_alma_error(self, mock_session_maker):
        """Test process_scf_duplicates_report with Alma API error"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.duplicate_report_path = "/test/path"
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_alma_client = Mock()
        mock_alma_client.analytics.get_report.side_effect = Exception("API Error")

        with patch('alma_item_checks_processor_service.services.scf_duplicates_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.AlmaApiClient',
                   return_value=mock_alma_client), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.logging'):

            # Should return early without crashing
            self.service.process_scf_duplicates_report()

    @patch('alma_item_checks_processor_service.services.scf_duplicates_service.SessionMaker')
    def test_process_scf_duplicates_report_no_results(self, mock_session_maker):
        """Test process_scf_duplicates_report with no results"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.api_key = "test_key"
        mock_institution.duplicate_report_path = "/test/path"
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        mock_alma_client = Mock()
        mock_report = Mock()
        mock_report.rows = []  # No results
        mock_alma_client.analytics.get_report.return_value = mock_report

        with patch('alma_item_checks_processor_service.services.scf_duplicates_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.AlmaApiClient',
                   return_value=mock_alma_client), \
             patch('alma_item_checks_processor_service.services.scf_duplicates_service.logging'):

            # Should return early without calling storage
            self.service.process_scf_duplicates_report()
