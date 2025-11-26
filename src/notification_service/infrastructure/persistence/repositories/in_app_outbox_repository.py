"""In-app outbox repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel
from notification_service.domain.entities.in_app.in_app_outbox import InAppOutbox
from notification_service.infrastructure.persistence.mappers.in_app_outbox_mapper import InAppOutboxMapper

class InAppOutboxRepository(GenericRepository[InAppOutboxModel, InAppOutbox]):
    """Repository for in-app outbox."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, InAppOutboxModel, InAppOutboxMapper())

