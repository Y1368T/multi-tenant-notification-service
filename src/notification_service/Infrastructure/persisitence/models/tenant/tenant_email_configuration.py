from sqlalchemy import UUID, Column, Integer, DateTime, String, Boolean, ForeignKey, UniqueConstraint,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..base import BaseModel
class TenantEmailConfigurationModel(BaseModel):
    __tablename__ = "tenant_email_configurations"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenant_id", primary_key=True)
    providerName = Column(String, name="provider_name", nullable=False)
    config = Column(JSONB, nullable=False, default={})
    priority = Column(Integer, nullable=False, default=1)
    isActive = Column(Boolean, name="is_active", default=True)
    rateLimitPerMinute = Column(Integer, name="rate_limit_per_minute", default=50)
    rateLimitPerHour = Column(Integer, name="rate_limit_per_hour", default=800)
    rateLimitPerDay = Column(Integer, name="rate_limit_per_day", default=8000)
    tenant = relationship("TenantModel", back_populates="emailConfigurations")
    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uix_tenant_email_provider'),
    )
