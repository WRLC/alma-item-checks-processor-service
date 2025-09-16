"""Tests for models/base.py"""

import pytest
from alma_item_checks_processor_service.models.base import Base


class TestBase:
    """Test cases for Base model"""

    def test_base_is_declarative_base(self):
        """Test that Base is a SQLAlchemy declarative base"""
        from sqlalchemy.orm import DeclarativeBase
        # Test that Base is a DeclarativeBase subclass
        assert issubclass(Base, DeclarativeBase)
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, 'registry')

    def test_base_metadata_exists(self):
        """Test that Base has metadata attribute"""
        assert Base.metadata is not None
