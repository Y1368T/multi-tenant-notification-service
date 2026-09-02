from sqlalchemy import UUID, Column, String, ForeignKey, UniqueConstraint, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class TelegramNotificationModel(BaseModel):
    __tablename__ = "telegramNotifications"

    recipientChatId = Column(String, name="recipientChatId", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="pending")
    isRead = Column(Boolean, name="isRead", nullable=False, default=False)
    externalId = Column(String, name="externalId", nullable=True, index=True)  # User ID in tenant's system
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("telegramTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    
    template = relationship("TelegramTemplateModel", back_populates="telegramNotifications")

    __table_args__ = (
        UniqueConstraint('templateId', 'recipientChatId', 'idempotencyKey', name='uix_telegram_notification'),
        Index('ix_telegram_notifications_external_id', 'externalId'),
    )
