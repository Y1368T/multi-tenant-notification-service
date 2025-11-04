from sqlalchemy import UUID, Column, String, Boolean,Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class SmsTemplateModel(BaseModel):
    __tablename__ = "sms_templates"

    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String, nullable=False)
    content = Column(JSONB, nullable=False,default=dict)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, nullable=False, default=1)
    service_name = Column(String, nullable=False)
    tenant = relationship("TenantModel", back_populates="sms_templates")
    sms_notifications = relationship("SMSNotificationModel", back_populates="template")
    sms_outboxes = relationship("SmsOutboxModel", back_populates="template")

    __table_args__ = (
        UniqueConstraint('tenant_id','service_name', 'template_name','version', name='uix_tenant_sms_template'),
    )