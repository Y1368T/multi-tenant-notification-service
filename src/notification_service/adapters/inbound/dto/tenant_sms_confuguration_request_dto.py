from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration

class TenantSMSConfigurationRequestDto(BaseModel):
    tenantId: UUID = Field(alias="tenant_id")
    providerName: str = Field(alias="provider_name")
    priority: int
    isActive: bool = Field(default=True, alias="is_active")
    rateLimitPerMinute: int = Field(default=30, alias="rate_limit_per_minute")
    rateLimitPerHour: int = Field(default=500, alias="rate_limit_per_hour")
    rateLimitPerDay: int = Field(default=5000, alias="rate_limit_per_day")
    config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "TenantSMSConfigurationRequestDto":
        return cls(
            tenantId=data["tenant_id"],
            providerName=data["provider_name"],
            priority=int(data.get("priority", 1)),
            isActive=bool(data.get("is_active", True)),
            rateLimitPerMinute=int(data.get("rate_limit_per_minute", 30)),
            rateLimitPerHour=int(data.get("rate_limit_per_hour", 500)),
            rateLimitPerDay=int(data.get("rate_limit_per_day", 5000)),
            config=data.get("config", {}),
        )

    def toEntity(self) -> TenantSMSConfiguration:
        return TenantSMSConfiguration(
            id=uuid4(),
            tenantId=self.tenantId,
            providerName=self.providerName,
            priroty=self.priority,
            isActive=self.isActive,
            rateLimitPerMinute=self.rateLimitPerMinute,
            rateLimitPerHour=self.rateLimitPerHour,
            rateLimitPerDay=self.rateLimitPerDay,
            config=self.config,
        )

class TenantSMSConfigurationResponseDTO(BaseModel):
    id: UUID
    tenantId: UUID = Field(alias="tenant_id")
    providerName: str = Field(alias="provider_name")
    priority: int
    isActive: bool = Field(alias="is_active")
    rateLimitPerMinute: int = Field(alias="rate_limit_per_minute")
    rateLimitPerHour: int = Field(alias="rate_limit_per_hour")
    rateLimitPerDay: int = Field(alias="rate_limit_per_day")
    config: Dict[str, Any] = Field(default_factory=dict)
    createdAt: Optional[datetime] = Field(default=None, alias="created_at")
    updatedAt: Optional[datetime] = Field(default=None, alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)

    @classmethod
    def fromEntityWithRelations(cls, config: TenantSMSConfiguration):
        return cls(
            id=config.id,
            tenantId=config.tenantId,
            providerName=config.providerName,
            priority=getattr(config, "priroty", 1),
            isActive=config.isActive,
            rateLimitPerMinute=config.rateLimitPerMinute,
            rateLimitPerHour=config.rateLimitPerHour,
            rateLimitPerDay=config.rateLimitPerDay,
            config=getattr(config, "config", {}) or {},
            createdAt=getattr(config, "createdAt", None),
            updatedAt=getattr(config, "updatedAt", None),
        )