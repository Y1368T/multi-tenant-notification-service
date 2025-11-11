from sqlalchemy import UUID, Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SMSNotificationModel(BaseModel):
    __tablename__ = "sms_notifications"

    recipientNumber = Column(String, name="recipient_number", nullable=False)
    messageContent = Column(JSONB, name="message_content", nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotencyKey = Column(String, name="idempotency_key", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("sms_templates.id", ondelete="SET NULL"), name="template_id", nullable=True)
    template = relationship("SmsTemplateModel", back_populates="smsNotifications")