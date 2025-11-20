from sqlalchemy import UUID, Column, Integer, DateTime, String, Boolean, ForeignKey, UniqueConstraint,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..base import BaseModel
class TenantEmailConfigurationModel(BaseModel):
    __tablename__ = "tenantEmailConfigurations"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", primary_key=True)
    providerName = Column(String, name="providerName", nullable=False)
    config = Column(JSONB, nullable=False, default={})
    priority = Column(Integer, nullable=False, default=1)
    isActive = Column(Boolean, name="isActive", default=True)
    rateLimitPerMinute = Column(Integer, name="rateLimitPerMinute", default=50)
    rateLimitPerHour = Column(Integer, name="rateLimitPerHour", default=800)
    rateLimitPerDay = Column(Integer, name="rateLimitPerDay", default=8000)
    tenant = relationship("TenantModel", back_populates="emailConfigurations")
    __table_args__ = (
        UniqueConstraint('tenantId', 'providerName', name='uix_tenant_email_provider'),
    )
