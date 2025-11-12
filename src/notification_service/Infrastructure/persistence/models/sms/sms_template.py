from sqlalchemy import UUID, Column, String, Boolean,Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SmsTemplateModel(BaseModel):
    __tablename__ = "sms_templates"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenant_id", nullable=False)
    templateName = Column(String, name="template_name", nullable=False)
    content = Column(JSONB, nullable=False,default=dict)
    isActive = Column(Boolean, name="is_active", default=True)
    version = Column(Integer, nullable=False, default=1)
    serviceName = Column(String, name="service_name", nullable=False)
    tenant = relationship("TenantModel", back_populates="smsTemplates")
    smsNotifications = relationship("SMSNotificationModel", back_populates="template")
    smsOutboxes = relationship("SmsOutboxModel", back_populates="template")

    __table_args__ = (
        UniqueConstraint('tenant_id','service_name', 'template_name','version', name='uix_tenant_sms_template'),
    )