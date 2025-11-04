from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
from ..base import BaseModel
from sqlalchemy import Column, String, Boolean, Integer, JSONB, ForeignKey,UniqueConstraint
from sqlalchemy.orm import relationship



class TenantInAppConfigurationModel(BaseModel):
    __tablename__ = "tenant_inapp_configurations"
    
    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    provider_name = Column(String, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    priority = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=50)
    rate_limit_per_hour = Column(Integer, default=800)
    rate_limit_per_day = Column(Integer, default=8000)
    tenant = relationship("TenantModel", back_populates="inapp_configurations")
    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uix_tenant_inapp_provider'),
    )