from sqlalchemy import Column, String, UUID, ForeignKey, UniqueConstraint, Boolean, Index
from sqlalchemy.orm import relationship
from ..base import BaseModel


class InAppNotificationModel(BaseModel):
    __tablename__ = "inAppNotifications"

    recipientUserId = Column(String, name="recipientUserId", nullable=False)
    messageContent = Column(String, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="unread")
    isRead = Column(Boolean, name="isRead", nullable=False, default=False)
    externalId = Column(String, name="externalId", nullable=True, index=True)  # User ID in tenant's system
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("inAppTemplates.id"), name="templateId", nullable=True)
    
    template = relationship("InAppTemplateModel", back_populates="inAppNotifications")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientUserId', 'idempotencyKey', name='uix_in_app_notification'),
        Index('ix_inapp_notifications_external_id', 'externalId'),
    )