from sqlalchemy import Column, String, UUID, ForeignKey, UniqueConstraint, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class EmailNotificationModel(BaseModel):
    __tablename__ = "emailNotifications"

    recipientEmail = Column(String, name="recipientEmail", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="pending")
    isRead = Column(Boolean, name="isRead", nullable=False, default=False)
    externalId = Column(String, name="externalId", nullable=True, index=True)  # User ID in tenant's system
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("emailTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)

    template = relationship("EmailTemplateModel", back_populates="emailNotifications")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientEmail', 'idempotencyKey', name='uix_email_notification'),
        Index('ix_email_notifications_external_id', 'externalId'),
    )