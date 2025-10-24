from sqlalchemy import UUID, Column, Integer, String, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import  relationship
from ..base import BaseModel
class EmailTemplateModel(BaseModel):
    __tablename__ = "email_templates"

    template_name = Column(String, unique=True, index=True, nullable=False)
    subject = Column(String, nullable=False)
    body_type = Column(String, nullable=False, default="html")  # e.g., 'html' or 'text'
    body = Column(String, nullable=False)
    file_urls = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, nullable=False, default=1)
    service_name = Column(String, nullable=False)
    tenant_id = Column(UUID, nullable=False)
    tenant = relationship("TenantModel", back_populates="email_templates")
    email_notifications = relationship("EmailNotificationModel", back_populates="template")
    email_outboxes = relationship("EmailOutboxModel", back_populates="template")
    __table_args__ = (
        UniqueConstraint('tenant_id', 'service_name', 'template_name', 'version', name='uix_email_template'),
    )