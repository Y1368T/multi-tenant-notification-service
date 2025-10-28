from sqlalchemy import UUID, Column, Integer, DateTime, String, Boolean, ForeignKey, UniqueConstraint,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..base import BaseModel
class TenantEmailConfigurationModel(BaseModel):
    __tablename__ = "tenant_email_configurations"

    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    provider_name = Column(String, nullable=False)
    config = Column(JSONB, nullable=False, default={})
    priority = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=50)
    rate_limit_per_hour = Column(Integer, default=800)
    rate_limit_per_day = Column(Integer, default=8000)
    tenant = relationship("TenantModel", back_populates="email_configurations")
    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uix_tenant_email_provider'),
    )
