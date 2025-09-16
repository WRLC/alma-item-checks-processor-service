"""Tests for blueprints/bp_institutions_api.py"""

import json
import pytest
from unittest.mock import Mock, patch
import azure.functions as func
from alma_item_checks_processor_service.blueprints.bp_institutions_api import (
    get_institutions, get_institution, create_institution, update_institution, delete_institution, get_institution_api_key
)


class TestBpInstitutionsApi:
    """Test cases for bp_institutions_api blueprint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_req = Mock(spec=func.HttpRequest)

    def create_mock_institution(self, id=1, name="Test Institution", code="test", api_key="test_key"):
        """Create a mock institution with proper attributes"""
        mock_inst = Mock()
        mock_inst.id = id
        mock_inst.name = name
        mock_inst.code = code
        mock_inst.api_key = api_key
        mock_inst.duplicate_report_path = None
        return mock_inst

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institutions_success(self, mock_session_maker):
        """Test successful institutions retrieval"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institutions = [
            self.create_mock_institution(1, "Institution 1", "inst1", "key1"),
            self.create_mock_institution(2, "Institution 2", "inst2", "key2")
        ]
        mock_institution_repo.get_all_institutions.return_value = mock_institutions

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = get_institutions(self.mock_req)

        assert response.status_code == 200
        mock_institution_repo.get_all_institutions.assert_called_once()

        # Verify response body contains expected data
        response_data = json.loads(response.get_body())
        assert len(response_data) == 2
        assert response_data[0]["name"] == "Institution 1"
        assert response_data[1]["name"] == "Institution 2"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institutions_exception(self, mock_session_maker):
        """Test institutions retrieval with exception"""
        mock_session_maker.side_effect = Exception("Database error")

        response = get_institutions(self.mock_req)

        assert response.status_code == 500

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_success(self, mock_session_maker):
        """Test successful single institution retrieval"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution = self.create_mock_institution(1, "Test Institution", "test", "test_key")
        mock_institution_repo.get_institution_by_id.return_value = mock_institution

        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = get_institution(self.mock_req)

        assert response.status_code == 200
        mock_institution_repo.get_institution_by_id.assert_called_once_with(1)

        # Verify response body
        response_data = json.loads(response.get_body())
        assert response_data["name"] == "Test Institution"
        assert response_data["id"] == 1

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_not_found(self, mock_session_maker):
        """Test single institution retrieval when not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.get_institution_by_id.return_value = None

        self.mock_req.route_params = {"id": "999"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = get_institution(self.mock_req)

        assert response.status_code == 404

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_success(self, mock_session_maker):
        """Test successful institution creation"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution = self.create_mock_institution(1, "Test Institution", "test", "test_key")
        mock_institution_repo.create_institution.return_value = mock_institution

        request_data = {
            "name": "Test Institution",
            "code": "test",
            "api_key": "test_key"
        }
        self.mock_req.get_json.return_value = request_data

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = create_institution(self.mock_req)

        assert response.status_code == 201
        mock_institution_repo.create_institution.assert_called_once()

        # Verify response body
        response_data = json.loads(response.get_body())
        assert response_data["name"] == "Test Institution"
        assert response_data["code"] == "test"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_missing_fields(self, mock_session_maker):
        """Test institution creation with missing required fields"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        request_data = {
            "name": "Test Institution"
            # Missing code and api_key
        }
        self.mock_req.get_json.return_value = request_data

        response = create_institution(self.mock_req)

        assert response.status_code == 400

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_success(self, mock_session_maker):
        """Test successful institution update"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution = self.create_mock_institution(1, "Updated Name", "test", "test_key")
        mock_institution_repo.update_institution.return_value = mock_institution

        self.mock_req.route_params = {"id": "1"}
        self.mock_req.get_json.return_value = {"name": "Updated Name"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = update_institution(self.mock_req)

        assert response.status_code == 200
        mock_institution_repo.update_institution.assert_called_once_with(1, name="Updated Name")

        # Verify response body
        response_data = json.loads(response.get_body())
        assert response_data["name"] == "Updated Name"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_not_found(self, mock_session_maker):
        """Test institution update when institution not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.update_institution.return_value = None

        self.mock_req.route_params = {"id": "999"}
        self.mock_req.get_json.return_value = {"name": "Updated Name"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = update_institution(self.mock_req)

        assert response.status_code == 404

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_delete_institution_success(self, mock_session_maker):
        """Test successful institution deletion"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.delete_institution.return_value = True

        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = delete_institution(self.mock_req)

        assert response.status_code == 200  # Blueprint returns 200, not 204
        mock_institution_repo.delete_institution.assert_called_once_with(1)

        # Verify response body
        response_data = json.loads(response.get_body())
        assert response_data["message"] == "Institution deleted successfully"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_delete_institution_not_found(self, mock_session_maker):
        """Test institution deletion when institution not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.delete_institution.return_value = False

        self.mock_req.route_params = {"id": "999"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = delete_institution(self.mock_req)

        assert response.status_code == 404

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_invalid_id(self, mock_session_maker):
        """Test get_institution with invalid ID causing ValueError"""
        self.mock_req.route_params = {"id": "invalid"}

        response = get_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Invalid institution ID"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_exception(self, mock_session_maker):
        """Test get_institution with unexpected exception"""
        mock_session_maker.side_effect = Exception("Database error")
        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = get_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_exception(self, mock_session_maker):
        """Test create_institution with unexpected exception"""
        mock_session_maker.side_effect = Exception("Database error")

        request_data = {
            "name": "Test Institution",
            "code": "test",
            "api_key": "test_key"
        }
        self.mock_req.get_json.return_value = request_data

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = create_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_json_exception(self, mock_session_maker):
        """Test create_institution with JSON parsing exception"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        self.mock_req.get_json.side_effect = Exception("JSON parse error")

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = create_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_repo_returns_none(self, mock_session_maker):
        """Test create_institution when repository returns None"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.create_institution.return_value = None

        request_data = {
            "name": "Test Institution",
            "code": "test",
            "api_key": "test_key"
        }
        self.mock_req.get_json.return_value = request_data

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = create_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Failed to create institution"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_invalid_id(self, mock_session_maker):
        """Test update_institution with invalid ID causing ValueError"""
        self.mock_req.route_params = {"id": "invalid"}
        self.mock_req.get_json.return_value = {"name": "Updated Name"}

        response = update_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Invalid institution ID"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_exception(self, mock_session_maker):
        """Test update_institution with unexpected exception"""
        mock_session_maker.side_effect = Exception("Database error")
        self.mock_req.route_params = {"id": "1"}
        self.mock_req.get_json.return_value = {"name": "Updated Name"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = update_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_delete_institution_invalid_id(self, mock_session_maker):
        """Test delete_institution with invalid ID causing ValueError"""
        self.mock_req.route_params = {"id": "invalid"}

        response = delete_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Invalid institution ID"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_delete_institution_exception(self, mock_session_maker):
        """Test delete_institution with unexpected exception"""
        mock_session_maker.side_effect = Exception("Database error")
        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = delete_institution(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_api_key_success(self, mock_session_maker):
        """Test successful API key retrieval"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution = self.create_mock_institution(1, "Test Institution", "test", "test_api_key")
        mock_institution_repo.get_institution_by_id.return_value = mock_institution

        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = get_institution_api_key(self.mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["api_key"] == "test_api_key"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_api_key_not_found(self, mock_session_maker):
        """Test API key retrieval when institution not found"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        mock_institution_repo = Mock()
        mock_institution_repo.get_institution_by_id.return_value = None

        self.mock_req.route_params = {"id": "999"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.InstitutionRepository',
                   return_value=mock_institution_repo):

            response = get_institution_api_key(self.mock_req)

        assert response.status_code == 404
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Institution not found"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_api_key_invalid_id(self, mock_session_maker):
        """Test API key retrieval with invalid ID"""
        self.mock_req.route_params = {"id": "invalid"}

        response = get_institution_api_key(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Invalid institution ID"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_get_institution_api_key_exception(self, mock_session_maker):
        """Test API key retrieval with unexpected exception"""
        mock_session_maker.side_effect = Exception("Database error")
        self.mock_req.route_params = {"id": "1"}

        with patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.logging'):
            response = get_institution_api_key(self.mock_req)

        assert response.status_code == 500
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Internal server error"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_create_institution_empty_body(self, mock_session_maker):
        """Test create_institution with empty request body"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        self.mock_req.get_json.return_value = None

        response = create_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Request body is required"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_empty_body(self, mock_session_maker):
        """Test update_institution with empty request body"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        self.mock_req.route_params = {"id": "1"}
        self.mock_req.get_json.return_value = None

        response = update_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "Request body is required"

    @patch('alma_item_checks_processor_service.blueprints.bp_institutions_api.SessionMaker')
    def test_update_institution_no_valid_fields(self, mock_session_maker):
        """Test update_institution with no valid fields to update"""
        mock_session = Mock()
        mock_session_maker.return_value.__enter__.return_value = mock_session

        self.mock_req.route_params = {"id": "1"}
        self.mock_req.get_json.return_value = {"invalid_field": "value"}

        response = update_institution(self.mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert response_data["error"] == "No valid fields to update"
