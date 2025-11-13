from sqlalchemy import UUID, Column, ForeignKey, String,Boolean,Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class TenantSMSConfigurationModel(BaseModel):
    __tablename__ = "tenant_sms_configurations"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenant_id", primary_key=True)
    providerName = Column(String, name="provider_name", nullable=False)
    config = Column(JSONB, nullable=False, default={})
    isActive = Column(Boolean, name="is_active", default=True)
    rateLimitPerMinute = Column(Integer, name="rate_limit_per_minute", default=30)
    rateLimitPerHour = Column(Integer, name="rate_limit_per_hour", default=500)
    rateLimitPerDay = Column(Integer, name="rate_limit_per_day", default=5000)

    tenant = relationship("TenantModel", back_populates="smsConfigurations")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uix_tenant_provider'),
    )