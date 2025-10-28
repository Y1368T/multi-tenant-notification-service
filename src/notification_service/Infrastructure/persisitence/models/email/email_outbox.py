from sqlalchemy import Boolean, Column, DateTime, Integer, String, UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel

class EmailOutboxModel(BaseModel):
    __tablename__ = "email_outbox"

    template_id = Column(UUID, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    recipient_email = Column(String, nullable=False)
    message_content = Column(JSONB, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime, nullable=True)
    last_error_message = Column(String, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    provider_attempted = Column(String, nullable=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="pending")

    template = relationship("EmailTemplateModel", back_populates="outbox_entries")