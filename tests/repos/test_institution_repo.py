"""Tests for repos/institution_repo.py"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from alma_item_checks_processor_service.repos.institution_repo import InstitutionRepository
from alma_item_checks_processor_service.models.institution import Institution


class TestInstitutionRepository:
    """Test cases for InstitutionRepository"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_session = Mock()
        self.repo = InstitutionRepository(self.mock_session)

    def test_init(self):
        """Test InstitutionRepository initialization"""
        assert self.repo.session == self.mock_session

    def test_get_institution_by_code_success(self):
        """Test successful institution retrieval by code"""
        mock_institution = Mock(spec=Institution)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = mock_institution
        self.mock_session.execute.return_value = mock_result

        result = self.repo.get_institution_by_code("test")

        assert result == mock_institution
        self.mock_session.execute.assert_called_once()

    def test_get_institution_by_code_not_found(self):
        """Test institution retrieval when not found"""
        self.mock_session.execute.side_effect = NoResultFound()

        with patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.get_institution_by_code("nonexistent")

        assert result is None

    def test_get_institution_by_code_sqlalchemy_error(self):
        """Test institution retrieval with SQLAlchemy error"""
        self.mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.get_institution_by_code("test")

        assert result is None

    def test_get_institution_by_code_unexpected_error(self):
        """Test institution retrieval with unexpected error"""
        self.mock_session.execute.side_effect = Exception("Unexpected error")

        with patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.get_institution_by_code("test")

        assert result is None

    def test_get_institution_by_id_success(self):
        """Test successful institution retrieval by ID"""
        mock_institution = Mock(spec=Institution)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = mock_institution
        self.mock_session.execute.return_value = mock_result

        result = self.repo.get_institution_by_id(1)

        assert result == mock_institution
        self.mock_session.execute.assert_called_once()

    def test_get_institution_by_id_not_found(self):
        """Test institution retrieval by ID when not found"""
        self.mock_session.execute.side_effect = NoResultFound()

        with patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.get_institution_by_id(999)

        assert result is None

    def test_get_all_institutions_success(self):
        """Test successful retrieval of all institutions"""
        mock_institutions = [Mock(spec=Institution), Mock(spec=Institution)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_institutions
        self.mock_session.execute.return_value = mock_result

        result = self.repo.get_all_institutions()

        assert result == mock_institutions
        self.mock_session.execute.assert_called_once()

    def test_get_all_institutions_sqlalchemy_error(self):
        """Test get_all_institutions with SQLAlchemy error"""
        self.mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.get_all_institutions()

        assert result == []

    def test_create_institution_success(self):
        """Test successful institution creation"""
        mock_institution = Mock(spec=Institution)

        with patch('alma_item_checks_processor_service.repos.institution_repo.Institution',
                   return_value=mock_institution):
            result = self.repo.create_institution(
                name="Test Institution",
                code="test",
                api_key="test_key",
                duplicate_report_path="/test/path"
            )

        assert result == mock_institution
        self.mock_session.add.assert_called_once_with(mock_institution)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_institution)

    def test_create_institution_sqlalchemy_error(self):
        """Test institution creation with SQLAlchemy error"""
        self.mock_session.commit.side_effect = SQLAlchemyError("Database error")

        with patch('alma_item_checks_processor_service.repos.institution_repo.Institution'), \
             patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.create_institution(
                name="Test Institution",
                code="test",
                api_key="test_key"
            )

        assert result is None
        self.mock_session.rollback.assert_called_once()

    def test_update_institution_success(self):
        """Test successful institution update"""
        mock_institution = Mock(spec=Institution)
        mock_institution.name = "Old Name"

        with patch.object(self.repo, 'get_institution_by_id', return_value=mock_institution):
            result = self.repo.update_institution(1, name="New Name")

        assert result == mock_institution
        assert mock_institution.name == "New Name"
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_institution)

    def test_update_institution_not_found(self):
        """Test institution update when institution not found"""
        with patch.object(self.repo, 'get_institution_by_id', return_value=None):
            result = self.repo.update_institution(999, name="New Name")

        assert result is None

    def test_update_institution_sqlalchemy_error(self):
        """Test institution update with SQLAlchemy error"""
        mock_institution = Mock(spec=Institution)
        self.mock_session.commit.side_effect = SQLAlchemyError("Database error")

        with patch.object(self.repo, 'get_institution_by_id', return_value=mock_institution), \
             patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.update_institution(1, name="New Name")

        assert result is None
        self.mock_session.rollback.assert_called_once()

    def test_delete_institution_success(self):
        """Test successful institution deletion"""
        mock_institution = Mock(spec=Institution)

        with patch.object(self.repo, 'get_institution_by_id', return_value=mock_institution):
            result = self.repo.delete_institution(1)

        assert result is True
        self.mock_session.delete.assert_called_once_with(mock_institution)
        self.mock_session.commit.assert_called_once()

    def test_delete_institution_not_found(self):
        """Test institution deletion when institution not found"""
        with patch.object(self.repo, 'get_institution_by_id', return_value=None):
            result = self.repo.delete_institution(999)

        assert result is False

    def test_delete_institution_sqlalchemy_error(self):
        """Test institution deletion with SQLAlchemy error"""
        mock_institution = Mock(spec=Institution)
        self.mock_session.commit.side_effect = SQLAlchemyError("Database error")

        with patch.object(self.repo, 'get_institution_by_id', return_value=mock_institution), \
             patch('alma_item_checks_processor_service.repos.institution_repo.logging'):
            result = self.repo.delete_institution(1)

        assert result is False
        self.mock_session.rollback.assert_called_once()
