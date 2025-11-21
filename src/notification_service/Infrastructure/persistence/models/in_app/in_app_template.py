from sqlalchemy import UUID, Column, String, UniqueConstraint,Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppTemplateModel(BaseModel):
    __tablename__ = "inAppTemplates"

    templateName = Column(String, name="templateName", unique=True, index=True, nullable=False)
    body = Column(JSONB, nullable=False,default={})
    isActive = Column(Boolean, name="isActive", default=True)
    version = Column(Integer, nullable=False, default=1)
    serviceName = Column(String, name="serviceName", nullable=False)
    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", nullable=False)
    tenant = relationship("TenantModel", back_populates="inAppTemplates")
    inAppNotifications = relationship("InAppNotificationModel", back_populates="template")
    inAppOutboxes = relationship("InAppOutboxModel", back_populates="template")
    __table_args__ = (
        UniqueConstraint('tenantId', 'serviceName', 'templateName', 'version', name='uix_in_app_template'),
    )