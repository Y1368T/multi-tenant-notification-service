"""WhatsApp template repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate
from notification_service.infrastructure.persistence.mappers.whatsapp_template_mapper import WhatsAppTemplateMapper

class WhatsAppTemplateRepository(GenericRepository[WhatsAppTemplateModel, WhatsAppTemplate]):
    """Repository for WhatsApp templates."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, WhatsAppTemplateModel, WhatsAppTemplateMapper())
