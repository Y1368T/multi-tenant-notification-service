"""Email template repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.email.email_template import EmailTemplateModel
from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.Infrastructure.persisitence.mappers.email_template_mapper import EmailTemplateMapper

class EmailTemplateRepository(GenericRepository[EmailTemplateModel, EmailTemplate]):
    """Repository for email templates."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailTemplateModel, EmailTemplateMapper)
