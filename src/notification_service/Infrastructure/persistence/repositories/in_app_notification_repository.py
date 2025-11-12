"""In-app notification repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.infrastructure.persistence.mappers.in_app_notification_mapper import InAppNotificationMapper

class InAppNotificationRepository(GenericRepository[InAppNotificationModel, InAppNotification]):
    """Repository for in-app notifications."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, InAppNotificationModel, InAppNotificationMapper())
