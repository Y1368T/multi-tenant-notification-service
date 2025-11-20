from sqlalchemy import Column, String,UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class EmailNotificationModel(BaseModel):
    __tablename__ = "emailNotifications"

    recipientEmail = Column(String, name="recipientEmail", nullable=False)
    messageContent = Column(JSONB, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="pending")
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("emailTemplates.id", ondelete="SET NULL"), name="templateId", nullable=True)

    template = relationship("EmailTemplateModel", back_populates="emailNotifications")