from sqlalchemy import Boolean, Column, DateTime, Integer, String, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel

class EmailOutboxModel(BaseModel):
    __tablename__ = "emailOutbox"

    templateId = Column(UUID, ForeignKey("emailTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    recipientEmail = Column(String, name="recipientEmail", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    retryCount = Column(Integer, name="retryCount", default=0)
    lastRetryAt = Column(DateTime, name="lastRetryAt", nullable=True)
    lastErrorMessage = Column(String, name="lastErrorMessage", nullable=True)
    nextRetryAt = Column(DateTime, name="nextRetryAt", nullable=True)
    providerAttempted = Column(String, name="providerAttempted", nullable=True)
    isSent = Column(Boolean, name="isSent", default=False)
    sentAt = Column(DateTime, name="sentAt", nullable=True)
    status = Column(String, nullable=False, default="pending")
    template = relationship("EmailTemplateModel", back_populates="emailOutboxes")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientEmail', 'idempotencyKey', name='uix_email_outbox'),
    )