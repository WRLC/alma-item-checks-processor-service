"""Tests for services/institution_service.py"""

import pytest
from unittest.mock import Mock
from alma_item_checks_processor_service.services.institution_service import InstitutionService


class TestInstitutionService:
    """Test cases for InstitutionService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_session = Mock()
        self.mock_repository = Mock()
        self.service = InstitutionService(self.mock_session)
        # Replace the repository with our mock
        self.service.repository = self.mock_repository

    def test_init(self):
        """Test InstitutionService initialization"""
        # Create a fresh service to test real initialization
        service = InstitutionService(self.mock_session)
        assert service.repository is not None

    def test_get_institution_by_code_success(self):
        """Test successful institution retrieval by code"""
        mock_institution = Mock()
        self.mock_repository.get_institution_by_code.return_value = mock_institution

        result = self.service.get_institution_by_code("test")

        assert result == mock_institution
        self.mock_repository.get_institution_by_code.assert_called_once_with("test")

    def test_get_institution_by_code_not_found(self):
        """Test institution retrieval when not found"""
        self.mock_repository.get_institution_by_code.return_value = None

        result = self.service.get_institution_by_code("nonexistent")

        assert result is None
        self.mock_repository.get_institution_by_code.assert_called_once_with("nonexistent")
