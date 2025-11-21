from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppNotificationModel(BaseModel):
    __tablename__ = "inAppNotifications"

    recipientUserId = Column(String, name="recipientUserId", nullable=False)
    messageContent = Column(String, name="messageContent", nullable=False)
    status = Column(String, nullable=False, default="unread")
    idempotencyKey = Column(String, name="idempotencyKey", unique=True, nullable=False)
    templateId = Column(UUID, ForeignKey("inAppTemplates.id"), name="templateId", nullable=True)
    
    template = relationship("InAppTemplateModel", back_populates="inAppNotifications")