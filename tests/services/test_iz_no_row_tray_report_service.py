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

    def test_process_staged_items_no_items(self):
        """Test _process_staged_items with no items"""
        result = self.service._process_staged_items([])
        assert result == (0, 0)

    def test_process_staged_items_missing_data(self):
        """Test _process_staged_items with missing barcode or institution"""
        entities = [
            {"RowKey": None, "institution_code": "doc"},  # Missing barcode
            {"RowKey": "12345", "institution_code": None},  # Missing institution
            {"RowKey": "67890", "institution_code": "doc"},  # Valid
        ]

        with patch.object(self.service, '_process_single_item') as mock_process:
            mock_process.return_value = {"success": True}
            processed, failed = self.service._process_staged_items(entities)

        assert processed == 1  # Only the valid one
        assert failed == 2  # Two failed due to missing data
        mock_process.assert_called_once_with("67890", "doc")

    def test_process_staged_items_report_no_staged_items(self):
        """Test process_staged_items_report when no staged items"""
        with patch.object(self.service, '_get_staged_items', return_value=[]), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):

            # Should return early without errors
            self.service.process_staged_items_report()

    def test_clear_staging_table_success(self):
        """Test successful staging table clearing"""
        staged_entities = [
            {"RowKey": "12345"},
            {"RowKey": "67890"}
        ]

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):
            self.service._clear_staging_table(staged_entities)

        # Should call delete_entity for each entity
        assert self.service.storage_service.delete_entity.call_count == 2

    def test_clear_staging_table_with_errors(self):
        """Test staging table clearing with some errors"""
        staged_entities = [{"RowKey": "12345"}]
        self.service.storage_service.delete_entity.side_effect = Exception("Delete error")

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):
            # Should not raise exception
            self.service._clear_staging_table(staged_entities)

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_staged_items_report_with_items(self, mock_session_maker):
        """Test process_staged_items_report when items are found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        # Mock staged entities
        staged_entities = [
            {"PartitionKey": "iz_no_row_tray", "RowKey": "12345", "institution_code": "test"}
        ]

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.service, '_get_staged_items', return_value=staged_entities), \
             patch.object(self.service, '_process_staged_items', return_value=(1, 0)), \
             patch.object(self.service, '_clear_staging_table'), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging') as mock_logging:

            self.service.process_staged_items_report()

        # Should complete processing
        mock_logging.info.assert_any_call("IZ no row tray report processing completed. Processed: 1, Failed: 0")

    @patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.SessionMaker')
    def test_process_staged_items_with_failed_items(self, mock_session_maker):
        """Test _process_staged_items with failed processing"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_service = Mock()
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution_service.get_institution_by_code.return_value = mock_institution

        staged_entities = [
            {"PartitionKey": "iz_no_row_tray", "RowKey": "12345", "institution_code": "test"}
        ]

        with patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.InstitutionService',
                   return_value=mock_institution_service), \
             patch.object(self.service, '_process_single_item', return_value={"success": False, "reason": "Test failure"}), \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging') as mock_logging:

            processed_count, failed_count = self.service._process_staged_items(staged_entities)

        assert processed_count == 0
        assert failed_count == 1
        mock_logging.warning.assert_called_with("Failed to process item 12345: Test failure")

    def test_clear_staging_table_with_empty_barcode(self):
        """Test _clear_staging_table with entity that has no barcode"""
        staged_entities = [
            {"PartitionKey": "iz_no_row_tray", "RowKey": None},  # Empty barcode
            {"PartitionKey": "iz_no_row_tray", "RowKey": "12345"}
        ]

        with patch.object(self.service.storage_service, 'delete_entity') as mock_delete, \
             patch('alma_item_checks_processor_service.services.iz_no_row_tray_report_service.logging'):

            self.service._clear_staging_table(staged_entities)

        # Should only delete the entity with a valid barcode
        mock_delete.assert_called_once()
