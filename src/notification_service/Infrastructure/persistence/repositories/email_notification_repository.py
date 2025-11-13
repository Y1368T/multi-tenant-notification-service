"""Email notification repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.infrastructure.persistence.mappers.email_notification_mapper import EmailNotificationMapper

class EmailNotificationRepository(GenericRepository[EmailNotificationModel, EmailNotification]):
    """Repository for email notifications."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailNotificationModel, EmailNotificationMapper())
