"""Service class for Institution model"""

from sqlalchemy.orm import Session

from alma_item_checks_processor_service.repos import InstitutionRepository
from alma_item_checks_processor_service.models import Institution


class InstitutionService:
    """Service class for Institution model"""

    def __init__(self, session: Session):
        self.repository = InstitutionRepository(session)

    def get_institution_by_code(self, code: str) -> Institution | None:
        """Get institution by code

        Args:
            code (str): The code of the institution
        Returns:
            Institution: The institution object
        """
        institution: Institution | None = self.repository.get_institution_by_code(code)

        return institution
