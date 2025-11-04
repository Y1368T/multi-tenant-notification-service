from sqlalchemy import UUID, Column, String, UniqueConstraint,Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class InAppTemplateModel(BaseModel):
    __tablename__ = "in_app_templates"

    template_name = Column(String, unique=True, index=True, nullable=False)
    body = Column(JSONB, nullable=False,default=dict)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, nullable=False, default=1)
    service_name = Column(String, nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tenant = relationship("TenantModel", back_populates="in_app_templates")
    in_app_notifications = relationship("InAppNotificationModel", back_populates="template")
    __table_args__ = (
        UniqueConstraint('tenant_id', 'service_name', 'template_name', 'version', name='uix_in_app_template'),
    )