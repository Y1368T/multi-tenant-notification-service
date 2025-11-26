"""SMS outbox repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.infrastructure.persistence.mappers.sms_outbox_mapper import SmsOutboxMapper

class SmsOutboxRepository(GenericRepository[SmsOutboxModel, SMSOutbox]):
    """Repository for SMS outbox."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, SmsOutboxModel, SmsOutboxMapper())
