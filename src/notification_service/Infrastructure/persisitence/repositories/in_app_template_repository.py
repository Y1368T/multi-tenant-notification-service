"""In-app template repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from notification_service.Infrastructure.persisitence.mappers.in_app_template_mapper import InAppTemplateMapper

class InAppTemplateRepository(GenericRepository[InAppTemplateModel, InAppTemplate]):
    """Repository for in-app templates."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, InAppTemplateModel, InAppTemplateMapper())
