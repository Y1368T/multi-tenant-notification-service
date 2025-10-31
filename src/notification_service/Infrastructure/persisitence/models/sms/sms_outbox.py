from sqlalchemy import Column, DateTime, Integer, String, Boolean, UUID, ForeignKey
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SmsOutboxModel(BaseModel):
    __tablename__ = "sms_outbox"

    template_id = Column(UUID, ForeignKey("sms_templates.id", ondelete="SET NULL"), nullable=True)
    recipient_number = Column(String, nullable=False)
    message_content = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime, nullable=True)
    last_error_message = Column(String, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    provider_attempted = Column(String, nullable=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="pending")
    template = relationship("SmsTemplateModel", back_populates="sms_outboxes")
    