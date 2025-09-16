"""Tests for models/institution.py"""

import pytest
from alma_item_checks_processor_service.models.institution import Institution


class TestInstitution:
    """Test cases for Institution model"""

    def test_institution_creation(self):
        """Test Institution model creation"""
        institution = Institution(
            name="Test Institution",
            code="test",
            api_key="test_api_key",
            duplicate_report_path="/test/path"
        )

        assert institution.name == "Test Institution"
        assert institution.code == "test"
        assert institution.api_key == "test_api_key"
        assert institution.duplicate_report_path == "/test/path"

    def test_institution_creation_minimal(self):
        """Test Institution model creation with minimal required fields"""
        institution = Institution(
            name="Test Institution",
            code="test",
            api_key="test_api_key"
        )

        assert institution.name == "Test Institution"
        assert institution.code == "test"
        assert institution.api_key == "test_api_key"
        assert institution.duplicate_report_path is None

    def test_institution_repr(self):
        """Test Institution string representation"""
        institution = Institution(
            name="Test Institution",
            code="test",
            api_key="test_api_key"
        )

        # Basic check that repr works and contains key info
        repr_str = repr(institution)
        assert "Institution" in repr_str
        assert "test" in repr_str
