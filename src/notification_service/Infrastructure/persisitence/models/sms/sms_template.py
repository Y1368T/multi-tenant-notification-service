from sqlalchemy import UUID, Column, String, Boolean,Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, relationship
from ..base import BaseModel
class SMSTemplateModel(BaseModel):
    __tablename__ = "sms_templates"

    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, nullable=False, default=1)
    service_name = Column(String, nullable=False)
    tenant = relationship("TenantModel", back_populates="sms_templates")
    sms_notifications = relationship("SMSNotificationModel", back_populates="template")
    sms_outboxes = relationship("SMSOutboxModel", back_populates="template")

    __table_args__ = (
        UniqueConstraint('tenant_id','service_name', 'template_name','version', name='uix_tenant_sms_template'),
    )