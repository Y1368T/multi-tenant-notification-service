from sqlalchemy import UUID, Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SMSNotificationModel(BaseModel):
    __tablename__ = "smsNotifications"

    recipientNumber = Column(String, name="recipientNumber", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("smsTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)
    template = relationship("SmsTemplateModel", back_populates="smsNotifications")