from sqlalchemy import Column, String, UUID, ForeignKey, Integer, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppOutboxModel(BaseModel):
    __tablename__ = "in_app_outbox"

    templateId = Column(UUID, ForeignKey("in_app_templates.id", ondelete="SET NULL"), name="template_id", nullable=True)
    recipientUserId = Column(String, name="recipient_user_id", nullable=False)
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

    template = relationship("InAppTemplateModel", back_populates="inAppOutboxes")
    __table_args__ = (
        UniqueConstraint('template_id', 'recipient_user_id', 'idempotency_key', name='uix_in_app_outbox'),
    )