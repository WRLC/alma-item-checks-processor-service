""" SQLAlchemy SessionMaker """
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker

from alma_item_checks_processor_service.config import SQLALCHEMY_CONNECTION_STRING

_db_engine: Engine | None = None
_session_maker: sessionmaker | None = None


def get_engine() -> Engine:
    """Get database engine, creating it if necessary"""
    global _db_engine
    if _db_engine is None:
        if SQLALCHEMY_CONNECTION_STRING is None:
            raise ValueError("SQLALCHEMY_CONNECTION_STRING environment variable not set")
        _db_engine = create_engine(SQLALCHEMY_CONNECTION_STRING, echo=True, pool_pre_ping=True)
    return _db_engine


def get_session_maker() -> sessionmaker:
    """Get session maker, creating it if necessary"""
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(bind=get_engine())
    return _session_maker


# For backward compatibility - lazy loading
def SessionMaker():
    """Lazy-loaded session maker"""
    return get_session_maker()()
