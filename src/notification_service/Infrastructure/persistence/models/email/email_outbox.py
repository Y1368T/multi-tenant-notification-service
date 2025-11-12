from sqlalchemy import Boolean, Column, DateTime, Integer, String, UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel

class EmailOutboxModel(BaseModel):
    __tablename__ = "email_outbox"

    templateId = Column(UUID, ForeignKey("email_templates.id", ondelete="SET NULL"), name="template_id", nullable=True)
    recipientEmail = Column(String, name="recipient_email", nullable=False)
    messageContent = Column(JSONB, name="message_content", nullable=False)
    idempotencyKey = Column(String, name="idempotency_key", unique=True, nullable=False)
    retryCount = Column(Integer, name="retry_count", default=0)
    lastRetryAt = Column(DateTime, name="last_retry_at", nullable=True)
    lastErrorMessage = Column(String, name="last_error_message", nullable=True)
    nextRetryAt = Column(DateTime, name="next_retry_at", nullable=True)
    providerAttempted = Column(String, name="provider_attempted", nullable=True)
    isSent = Column(Boolean, name="is_sent", default=False)
    sentAt = Column(DateTime, name="sent_at", nullable=True)
    status = Column(String, nullable=False, default="pending")
    template = relationship("EmailTemplateModel", back_populates="emailOutboxes")