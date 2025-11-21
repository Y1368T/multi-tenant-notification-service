from sqlalchemy import UUID, Column, ForeignKey, String, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel

class TenantInAppConfigurationModel(BaseModel):
    __tablename__ = "tenantInappConfigurations"
    
    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", primary_key=True)
    providerName = Column(String, name="providerName", nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    config = Column(JSONB, nullable=False, default={})
    isActive = Column(Boolean, name="isActive", default=True)
    rateLimitPerMinute = Column(Integer, name="rateLimitPerMinute", default=40)
    rateLimitPerHour = Column(Integer, name="rateLimitPerHour", default=600)
    rateLimitPerDay = Column(Integer, name="rateLimitPerDay", default=6000)
    tenant = relationship("TenantModel", back_populates="inAppConfigurations")
    __table_args__ = (
        UniqueConstraint('tenantId', 'providerName', name='uix_tenant_inapp_provider'),
    )