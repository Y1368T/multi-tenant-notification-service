from sqlalchemy import UUID, UUID, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, ForeignKey, relationship
from ..base import BaseModel
class SMSNotificationModel(BaseModel):
    __tablename__ = "sms_notifications"

    recipient_number = Column(String, nullable=False)
    message_content = Column(JSONB, nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotency_key = Column(String, unique=True, nullable=False)
    template_id = Column(UUID, ForeignKey("sms_templates.id", ondelete="SET NULL"), nullable=True)
    template = relationship("SMSTemplateModel", back_populates="sms_notifications")