"""Email outbox repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.email.email_outbox import EmailOutboxModel
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.Infrastructure.persisitence.mappers.email_outbox_mapper import EmailOutboxMapper

class EmailOutboxRepository(GenericRepository[EmailOutboxModel, EmailOutbox]):
    """Repository for email outbox."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailOutboxModel, EmailOutboxMapper())
