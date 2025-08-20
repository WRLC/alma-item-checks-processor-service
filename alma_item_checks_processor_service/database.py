""" SQLAlchemy SessionMaker """
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker

from alma_item_checks_processor_service.config import SQLALCHEMY_CONNECTION_STRING

DB_Engine: Engine = create_engine(SQLALCHEMY_CONNECTION_STRING, echo=True, pool_pre_ping=True)
SessionMaker: sessionmaker = sessionmaker(bind=DB_Engine)
