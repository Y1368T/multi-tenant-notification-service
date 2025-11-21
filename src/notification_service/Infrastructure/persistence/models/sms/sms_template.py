from sqlalchemy import UUID, Column, String, Boolean,Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SmsTemplateModel(BaseModel):
    __tablename__ = "smsTemplates"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", nullable=False)
    templateName = Column(String, name="templateName", nullable=False)
    content = Column(JSONB, nullable=False,default=dict)
    isActive = Column(Boolean, name="isActive", default=True)
    version = Column(Integer, nullable=False, default=1)
    serviceName = Column(String, name="serviceName", nullable=False)
    tenant = relationship("TenantModel", back_populates="smsTemplates")
    smsNotifications = relationship("SMSNotificationModel", back_populates="template")
    smsOutboxes = relationship("SmsOutboxModel", back_populates="template")

    __table_args__ = (
        UniqueConstraint('tenantId','serviceName', 'templateName','version', name='uix_tenant_sms_template'),
    )