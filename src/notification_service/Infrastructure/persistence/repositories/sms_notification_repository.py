"""SMS notification repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.infrastructure.persistence.mappers.sms_notification_mapper import SmsNotificationMapper

class SmsNotificationRepository(GenericRepository[SMSNotificationModel, SMSNotification]):
    """Repository for SMS notifications."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, SMSNotificationModel, SmsNotificationMapper())
