from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.telegram.telegram_notification import TelegramNotificationModel
from notification_service.domain.entities.telegram.telegram_notification import TelegramNotification
from notification_service.infrastructure.persistence.mappers.telegram_notification_mapper import TelegramNotificationMapper


class TelegramNotificationRepository(GenericRepository[TelegramNotificationModel, TelegramNotification]):
    """Repository for Telegram notifications."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TelegramNotificationModel, TelegramNotificationMapper())
