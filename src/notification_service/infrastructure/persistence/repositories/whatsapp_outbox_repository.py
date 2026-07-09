"""WhatsApp outbox repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.domain.entities.whatsapp.whatsapp_outbox import WhatsAppOutbox
from notification_service.infrastructure.persistence.mappers.whatsapp.whatsapp_outbox_mapper import WhatsAppOutboxMapper

class WhatsAppOutboxRepository(GenericRepository[WhatsAppOutboxModel, WhatsAppOutbox]):
    """Repository for WhatsApp outbox."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, WhatsAppOutboxModel, WhatsAppOutboxMapper())
