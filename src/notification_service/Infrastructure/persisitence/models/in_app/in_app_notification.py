from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppNotificationModel(BaseModel):
    __tablename__ = "in_app_notifications"

    recipient_user_id = Column(String, nullable=False)
    message_content = Column(String, nullable=False)
    status = Column(String, nullable=False, default="unread")
    idempotency_key = Column(String, unique=True, nullable=False)
    template_id = Column(UUID, ForeignKey("in_app_templates.id"), nullable=True)
    
    template = relationship("InAppTemplateModel", back_populates="in_app_notifications")