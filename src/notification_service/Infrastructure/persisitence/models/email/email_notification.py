from sqlalchemy import Column, String,UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class EmailNotificationModel(BaseModel):
    __tablename__ = "email_notifications"

    recipient_email = Column(String, nullable=False)
    message_content = Column(JSONB, nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotency_key = Column(String, unique=True, nullable=False)
    template_id = Column(UUID, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)

    template = relationship("EmailTemplateModel", back_populates="email_notifications")