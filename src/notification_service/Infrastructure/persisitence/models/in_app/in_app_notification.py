from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppNotificationModel(BaseModel):
    __tablename__ = "in_app_notifications"

    recipientUserId = Column(String, name="recipient_user_id", nullable=False)
    messageContent = Column(String, name="message_content", nullable=False)
    status = Column(String, nullable=False, default="unread")
    idempotencyKey = Column(String, name="idempotency_key", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("in_app_templates.id"), name="template_id", nullable=True)
    
    template = relationship("InAppTemplateModel", back_populates="inAppNotifications")