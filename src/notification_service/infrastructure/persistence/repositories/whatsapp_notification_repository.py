"""WhatsApp notification repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel
from notification_service.domain.entities.whatsapp.whatsapp_notification import WhatsAppNotification
from notification_service.infrastructure.persistence.mappers.whatsapp.whatsapp_notification_mapper import WhatsAppNotificationMapper

class WhatsAppNotificationRepository(GenericRepository[WhatsAppNotificationModel, WhatsAppNotification]):
    """Repository for WhatsApp notifications."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, WhatsAppNotificationModel, WhatsAppNotificationMapper())
