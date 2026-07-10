from sqlalchemy import Column, DateTime, Integer, String, Boolean, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class WhatsAppOutboxModel(BaseModel):
    __tablename__ = "whatsAppOutbox"

    templateId = Column(UUID, ForeignKey("whatsAppTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    recipientNumber = Column(String, name="recipientNumber", nullable=False)
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
    template = relationship("WhatsAppTemplateModel", back_populates="whatsAppOutboxes")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientNumber', 'idempotencyKey', name='uix_whatsApp_outbox'),
    )
    