from sqlalchemy import UUID, Column, Integer, String, Boolean, UniqueConstraint ,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class EmailTemplateModel(BaseModel):
    __tablename__ = "emailTemplates"

    templateName = Column(String, name="templateName", unique=True, index=True, nullable=False)
    subject = Column(String, nullable=False)
    bodyType = Column(String, name="bodyType", nullable=False, default="html")  # e.g., 'html' or 'text'
    body = Column(JSONB, nullable=False, default=dict)
    fileUrls = Column(String, name="fileUrls", nullable=True)
    isActive = Column(Boolean, name="isActive", default=True)
    version = Column(Integer, nullable=False, default=1)
    serviceName = Column(String, name="serviceName", nullable=False)
    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", nullable=False)
    tenant = relationship("TenantModel", back_populates="emailTemplates")
    emailNotifications = relationship("EmailNotificationModel", back_populates="template")
    emailOutboxes = relationship("EmailOutboxModel", back_populates="template")
    __table_args__ = (
        UniqueConstraint('tenantId', 'serviceName', 'templateName', 'version', name='uix_email_template'),
    )