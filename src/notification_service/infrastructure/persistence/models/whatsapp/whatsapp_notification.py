from sqlalchemy import UUID, Column, Integer, String, ForeignKey, UniqueConstraint, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class WhatsAppNotificationModel(BaseModel):
    __tablename__ = "whatsAppNotifications"

    recipientNumber = Column(String, name="recipientNumber", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="pending")
    isRead = Column(Boolean, name="isRead", nullable=False, default=False)
    externalId = Column(String, name="externalId", nullable=True, index=True)  # User ID in tenant's system
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("whatsAppTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    template = relationship("WhatsAppTemplateModel", back_populates="whatsAppNotifications")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientNumber', 'idempotencyKey', name='uix_whatsApp_notification'),
        Index('ix_whatsApp_notifications_external_id', 'externalId'),
    )