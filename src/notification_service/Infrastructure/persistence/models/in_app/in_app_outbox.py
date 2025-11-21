from sqlalchemy import Column, String, UUID, ForeignKey, Integer, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppOutboxModel(BaseModel):
    __tablename__ = "inAppOutbox"

    templateId = Column(UUID, ForeignKey("inAppTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    recipientUserId = Column(String, name="recipientUserId", nullable=False)
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

    template = relationship("InAppTemplateModel", back_populates="inAppOutboxes")
    __table_args__ = (
        UniqueConstraint('templateId', 'recipientUserId', 'idempotencyKey', name='uix_in_app_outbox'),
    )