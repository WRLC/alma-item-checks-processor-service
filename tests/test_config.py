"""Tests for config.py"""

import pytest
from unittest.mock import patch
import alma_item_checks_processor_service.config as config


class TestConfig:
    """Test cases for config module"""

    def test_skip_locations_exists(self):
        """Test that SKIP_LOCATIONS is defined"""
        assert hasattr(config, 'SKIP_LOCATIONS')
        assert isinstance(config.SKIP_LOCATIONS, list)

    def test_provenance_exists(self):
        """Test that PROVENANCE is defined"""
        assert hasattr(config, 'PROVENANCE')
        assert isinstance(config.PROVENANCE, list)

    def test_excluded_notes_exists(self):
        """Test that EXCLUDED_NOTES is defined"""
        assert hasattr(config, 'EXCLUDED_NOTES')
        assert isinstance(config.EXCLUDED_NOTES, list)

    def test_checked_iz_locations_exists(self):
        """Test that CHECKED_IZ_LOCATIONS is defined"""
        assert hasattr(config, 'CHECKED_IZ_LOCATIONS')
        assert isinstance(config.CHECKED_IZ_LOCATIONS, list)

    @patch.dict('os.environ', {'API_CLIENT_TIMEOUT': '120'})
    def test_api_client_timeout_from_env(self):
        """Test API_CLIENT_TIMEOUT reads from environment"""
        # Reload the module to pick up environment variable
        import importlib
        importlib.reload(config)
        assert config.API_CLIENT_TIMEOUT == 120

    def test_default_api_client_timeout(self):
        """Test default API_CLIENT_TIMEOUT value"""
        # This test assumes no API_CLIENT_TIMEOUT env var is set
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            importlib.reload(config)
            assert config.API_CLIENT_TIMEOUT == 90

    def test_storage_connection_string_config(self):
        """Test that storage connection string config exists"""
        assert hasattr(config, 'STORAGE_CONNECTION_STRING')

    def test_queue_names_config(self):
        """Test that queue name configurations exist"""
        queue_configs = [
            'FETCH_ITEM_QUEUE',
            'UPDATE_QUEUE',
            'NOTIFICATION_QUEUE'
        ]
        for queue_config in queue_configs:
            assert hasattr(config, queue_config)

    def test_container_names_config(self):
        """Test that container name configurations exist"""
        container_configs = [
            'UPDATED_ITEMS_CONTAINER',
            'REPORTS_CONTAINER'
        ]
        for container_config in container_configs:
            assert hasattr(config, container_config)

    def test_table_names_config(self):
        """Test that table name configurations exist"""
        table_configs = [
            'SCF_NO_ROW_TRAY_STAGE_TABLE',
            'SCF_NO_ROW_TRAY_REPORT_TABLE',
            'IZ_NO_ROW_TRAY_STAGE_TABLE'
        ]
        for table_config in table_configs:
            assert hasattr(config, table_config)

    def test_cron_schedule_configs(self):
        """Test that cron schedule configurations exist"""
        cron_configs = [
            'SCF_NO_ROW_TRAY_REPORT_NCRON',
            'SCF_DUPLICATES_REPORT_NCRON',
            'IZ_NO_ROW_TRAY_NCRON'
        ]
        for cron_config in cron_configs:
            assert hasattr(config, cron_config)
