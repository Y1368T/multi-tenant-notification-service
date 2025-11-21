from sqlalchemy import UUID, Column, ForeignKey, String,Boolean,Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class TenantSMSConfigurationModel(BaseModel):
    __tablename__ = "tenantSmsConfigurations"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", primary_key=True)
    providerName = Column(String, name="providerName", nullable=False)
    config = Column(JSONB, nullable=False, default={})
    isActive = Column(Boolean, name="isActive", default=True)
    rateLimitPerMinute = Column(Integer, name="rateLimitPerMinute", default=30)
    rateLimitPerHour = Column(Integer, name="rateLimitPerHour", default=500)
    rateLimitPerDay = Column(Integer, name="rateLimitPerDay", default=5000)

    tenant = relationship("TenantModel", back_populates="smsConfigurations")

    __table_args__ = (
        UniqueConstraint('tenantId', 'providerName', name='uix_tenant_provider'),
    )