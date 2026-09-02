from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.telegram.telegram_outbox import TelegramOutboxModel
from notification_service.domain.entities.telegram.telegram_outbox import TelegramOutbox
from notification_service.infrastructure.persistence.mappers.telegram_outbox_mapper import TelegramOutboxMapper


class TelegramOutboxRepository(GenericRepository[TelegramOutboxModel, TelegramOutbox]):
    """Repository for Telegram outboxes."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TelegramOutboxModel, TelegramOutboxMapper())
