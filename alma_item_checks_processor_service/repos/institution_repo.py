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
            logging.error(
                f"InstitutionRepo.get_institution_by_code: No such institution: {code}"
            )
            return None
        except SQLAlchemyError as e:
            logging.error(
                f"InstitutionRepo.get_institution_by_code: SQLAlchemyError: {e}"
            )
            return None
        except Exception as e:
            logging.error(
                f"InstitutionRepo.get_institution_by_code: Unexpected error: {e}"
            )
            return None

    def get_institution_by_id(self, institution_id: int) -> Institution | None:
        """Get institution by id

        Args:
            institution_id (int): The id of the institution

        Returns:
            Institution: The institution object or None
        """
        stmt: Select = Select(Institution).where(Institution.id == institution_id)
        try:
            return self.session.execute(stmt).scalars().first()
        except NoResultFound:
            logging.error(
                f"InstitutionRepo.get_institution_by_id: No such institution: {institution_id}"
            )
            return None
        except SQLAlchemyError as e:
            logging.error(
                f"InstitutionRepo.get_institution_by_id: SQLAlchemyError: {e}"
            )
            return None
        except Exception as e:
            logging.error(
                f"InstitutionRepo.get_institution_by_id: Unexpected error: {e}"
            )
            return None

    def get_all_institutions(self) -> list[Institution]:
        """Get all institutions

        Returns:
            list[Institution]: List of all institutions
        """
        stmt: Select = Select(Institution)
        try:
            return list(self.session.execute(stmt).scalars().all())
        except SQLAlchemyError as e:
            logging.error(f"InstitutionRepo.get_all_institutions: SQLAlchemyError: {e}")
            return []
        except Exception as e:
            logging.error(
                f"InstitutionRepo.get_all_institutions: Unexpected error: {e}"
            )
            return []

    def create_institution(
        self,
        name: str,
        code: str,
        api_key: str,
        duplicate_report_path: str | None = None,
    ) -> Institution | None:
        """Create a new institution

        Args:
            name (str): The name of the institution
            code (str): The code of the institution
            api_key (str): The API key of the institution
            duplicate_report_path (str | None): The duplicate report path

        Returns:
            Institution | None: The created institution or None if failed
        """
        try:
            institution = Institution(
                name=name,
                code=code,
                api_key=api_key,
                duplicate_report_path=duplicate_report_path,
            )
            self.session.add(institution)
            self.session.commit()
            self.session.refresh(institution)
            return institution
        except SQLAlchemyError as e:
            logging.error(f"InstitutionRepo.create_institution: SQLAlchemyError: {e}")
            self.session.rollback()
            return None
        except Exception as e:
            logging.error(f"InstitutionRepo.create_institution: Unexpected error: {e}")
            self.session.rollback()
            return None

    def update_institution(self, institution_id: int, **updates) -> Institution | None:
        """Update an institution

        Args:
            institution_id (int): The id of the institution
            **updates: Fields to update

        Returns:
            Institution | None: The updated institution or None if failed
        """
        try:
            institution = self.get_institution_by_id(institution_id)
            if not institution:
                return None

            for field, value in updates.items():
                if hasattr(institution, field):
                    setattr(institution, field, value)

            self.session.commit()
            self.session.refresh(institution)
            return institution
        except SQLAlchemyError as e:
            logging.error(f"InstitutionRepo.update_institution: SQLAlchemyError: {e}")
            self.session.rollback()
            return None
        except Exception as e:
            logging.error(f"InstitutionRepo.update_institution: Unexpected error: {e}")
            self.session.rollback()
            return None

    def delete_institution(self, institution_id: int) -> bool:
        """Delete an institution

        Args:
            institution_id (int): The id of the institution

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            institution = self.get_institution_by_id(institution_id)
            if not institution:
                return False

            self.session.delete(institution)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logging.error(f"InstitutionRepo.delete_institution: SQLAlchemyError: {e}")
            self.session.rollback()
            return False
        except Exception as e:
            logging.error(f"InstitutionRepo.delete_institution: Unexpected error: {e}")
            self.session.rollback()
            return False
