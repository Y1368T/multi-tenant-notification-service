from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration

class TenantSMSConfigurationRequestDto(BaseModel):
    tenant_id: UUID
    provider_name: str
    priority: int
    is_active: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500
    rate_limit_per_day: int = 5000
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TenantSMSConfigurationRequestDto":
        return cls(
            tenant_id=data["tenant_id"],
            provider_name=data["provider_name"],
            priority=int(data.get("priority", 1)),
            is_active=bool(data.get("is_active", True)),
            rate_limit_per_minute=int(data.get("rate_limit_per_minute", 30)),
            rate_limit_per_hour=int(data.get("rate_limit_per_hour", 500)),
            rate_limit_per_day=int(data.get("rate_limit_per_day", 5000)),
            config=data.get("config", {}),
        )

    def to_entity(self) -> TenantSMSConfiguration:
        return TenantSMSConfiguration(
            id=uuid4(),
            tenant_id=self.tenant_id,
            provider_name=self.provider_name,
            priority=self.priority,
            is_active=self.is_active,
            rate_limit_per_minute=self.rate_limit_per_minute,
            rate_limit_per_hour=self.rate_limit_per_hour,
            rate_limit_per_day=self.rate_limit_per_day,
            config=self.config,
        )

class TenantSMSConfigurationResponseDTO(BaseModel):
    id: UUID
    tenant_id: UUID
    provider_name: str
    priority: int
    is_active: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_entity_with_relations(cls, config: TenantSMSConfiguration):
        return cls(
            id=config.id,
            tenant_id=config.tenant_id,
            provider_name=config.provider_name,
            priority=getattr(config, "priority", 1),
            is_active=config.is_active,
            rate_limit_per_minute=config.rate_limit_per_minute,
            rate_limit_per_hour=config.rate_limit_per_hour,
            rate_limit_per_day=config.rate_limit_per_day,
            config=getattr(config, "config", {}) or {},
            created_at=getattr(config, "created_at", None),
            updated_at=getattr(config, "updated_at", None),
        )