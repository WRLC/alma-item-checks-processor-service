"""Repository for Institution model"""
import logging

from sqlalchemy import Select
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import Session

from alma_item_checks_processor_service.models.institution import Institution


class InstitutionRepository:
    """Repository for Institution model"""
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_institution_by_code(self, code: str) -> Institution | None:
        """Get institution by code

        Args:
            code (str): The code of the institution

        Returns:
            Institution: The institution object
        """
        stmt: Select = Select(Institution).where(Institution.code == code)
        try:
            return self.session.execute(stmt).scalars().first()
        except NoResultFound:
            logging.error(f'InstitutionRepo.get_institution_by_code: No such institution: {code}')
            return None
        except SQLAlchemyError as e:
            logging.error(f'InstitutionRepo.get_institution_by_code: SQLAlchemyError: {e}')
            return None
        except Exception as e:
            logging.error(f'InstitutionRepo.get_institution_by_code: Unexpected error: {e}')
            return None
