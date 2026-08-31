from sqlalchemy import Column, DateTime, Integer, String, Boolean, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class TelegramOutboxModel(BaseModel):
    __tablename__ = "telegramOutbox"

    templateId = Column(UUID, ForeignKey("telegramTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    recipientChatId = Column(String, name="recipientChatId", nullable=False)
    messageContent = Column(String, name="messageContent", nullable=False)
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    retryCount = Column(Integer, name="retryCount", default=0)
    lastRetryAt = Column(DateTime, name="lastRetryAt", nullable=True)
    lastErrorMessage = Column(String, name="lastErrorMessage", nullable=True)
    nextRetryAt = Column(DateTime, name="nextRetryAt", nullable=True)
    providerAttempted = Column(String, name="providerAttempted", nullable=True)
    isSent = Column(Boolean, name="isSent", default=False)
    sentAt = Column(DateTime, name="sentAt", nullable=True)
    status = Column(String, nullable=False, default="pending")
    callbackUrl = Column(String, name="callbackUrl", nullable=True)
    callbackHeaders = Column(JSONB, name="callbackHeaders", nullable=True)
    
    template = relationship("TelegramTemplateModel", back_populates="telegramOutboxes")

    __table_args__ = (
        UniqueConstraint('templateId', 'recipientChatId', 'idempotencyKey', name='uix_telegram_outbox'),
    )
