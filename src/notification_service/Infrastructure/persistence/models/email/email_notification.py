from sqlalchemy import Column, String,UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class EmailNotificationModel(BaseModel):
    __tablename__ = "email_notifications"

    recipientEmail = Column(String, name="recipient_email", nullable=False)
    messageContent = Column(JSONB, name="message_content", nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotencyKey = Column(String, name="idempotency_key", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("email_templates.id", ondelete="SET NULL"), name="template_id", nullable=True)

    template = relationship("EmailTemplateModel", back_populates="emailNotifications")