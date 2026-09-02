from sqlalchemy import UUID, Column, String, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel


class TenantTelegramConfigurationModel(BaseModel):
    __tablename__ = "tenantTelegramConfigurations"

    tenantId = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", nullable=False)
    providerName = Column(String, name="providerName", nullable=False)
    priority = Column(Integer, default=1)
    isActive = Column(Boolean, name="isActive", default=True)
    rateLimitPerMinute = Column(Integer, name="rateLimitPerMinute", default=30)
    rateLimitPerHour = Column(Integer, name="rateLimitPerHour", default=500)
    rateLimitPerDay = Column(Integer, name="rateLimitPerDay", default=5000)
    config = Column(JSONB, nullable=False, default=dict)
    
    tenant = relationship("TenantModel", back_populates="telegramConfigurations")

    __table_args__ = (
        UniqueConstraint('tenantId', 'providerName', name='uix_tenant_telegram_config'),
    )
