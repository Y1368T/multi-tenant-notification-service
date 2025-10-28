from sqlalchemy import UUID, Column, ForeignKey, String,Boolean,Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..base import BaseModel
class TenantSMSConfigurationModel(BaseModel):
    __tablename__ = "tenant_sms_configurations"

    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    provider_name = Column(String, nullable=False)
    config = Column(JSONB, nullable=False, default={})
    api_key = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=30)
    rate_limit_per_hour = Column(Integer, default=500)
    rate_limit_per_day = Column(Integer, default=5000)

    tenant = relationship("TenantModel", back_populates="sms_configurations")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uix_tenant_provider'),
    )