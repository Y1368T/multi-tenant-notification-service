from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.telegram.telegram_template import TelegramTemplateModel
from notification_service.domain.entities.telegram.telegram_template import TelegramTemplate
from notification_service.infrastructure.persistence.mappers.telegram_template_mapper import TelegramTemplateMapper


class TelegramTemplateRepository(GenericRepository[TelegramTemplateModel, TelegramTemplate]):
    """Repository for Telegram templates."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TelegramTemplateModel, TelegramTemplateMapper())
