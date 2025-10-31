from sqlalchemy import UUID, Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SMSNotificationModel(BaseModel):
    __tablename__ = "sms_notifications"

    recipient_number = Column(String, nullable=False)
    message_content = Column(JSONB, nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotency_key = Column(String, unique=True, nullable=False)
    template_id = Column(UUID, ForeignKey("sms_templates.id", ondelete="SET NULL"), nullable=True)
    template = relationship("SmsTemplateModel", back_populates="sms_notifications")