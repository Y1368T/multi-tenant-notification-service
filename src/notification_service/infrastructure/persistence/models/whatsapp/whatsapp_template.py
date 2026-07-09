from sqlalchemy import UUID, Column, String, Boolean,Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class WhatsAppTemplateModel(BaseModel):
    __tablename__ = "whatsAppTemplates"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", nullable=False)
    templateName = Column(String, name="templateName", nullable=False)
    content = Column(JSONB, nullable=False,default=dict)
    isActive = Column(Boolean, name="isActive", default=True)
    version = Column(Integer, nullable=False, default=1)
    serviceName = Column(String, name="serviceName", nullable=False)
    tenant = relationship("TenantModel", back_populates="whatsAppTemplates")
    whatsAppNotifications = relationship("WhatsAppNotificationModel", back_populates="template")
    whatsAppOutboxes = relationship("WhatsAppOutboxModel", back_populates="template")

    __table_args__ = (
        UniqueConstraint('tenantId','serviceName', 'templateName','version', name='uix_tenant_whatsApp_template'),
    )