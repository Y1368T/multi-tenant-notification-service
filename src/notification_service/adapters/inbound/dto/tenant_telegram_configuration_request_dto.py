from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID, uuid4
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_telegram_configuration import TenantTelegramConfiguration
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput


class TenantTelegramConfigurationRequestDto(BaseModel):
    """Request DTO for creating/updating tenant Telegram configurations."""
    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int = Field(default=1)
    isActive: bool = Field(default=True, alias="isActive")
    rateLimitPerMinute: int = Field(default=30, alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(default=500, alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(default=5000, alias="rateLimitPerDay")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telegram provider configuration. For the built-in 'telegram' provider, include {'bot_token': 'YOUR_BOT_TOKEN'}."
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=False,
        json_schema_extra={
            "example": {
                "tenantId": "123e4567-e89b-12d3-a456-426614174000",
                "providerName": "telegram",
                "priority": 1,
                "isActive": True,
                "rateLimitPerMinute": 30,
                "rateLimitPerHour": 500,
                "rateLimitPerDay": 5000,
                "config": {
                    "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                }
            }
        }
    )

    @field_validator('providerName')
    @classmethod
    def validateProviderName(cls, v: str) -> str:
        sanitized = validateStringInput(v, fieldName='providerName', maxLength=50)
        return sanitized

    @field_validator('priority')
    @classmethod
    def validatePriority(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Priority must be at least 1")
        if v > 100:
            raise ValueError("Priority must be at most 100")
        return v

    @field_validator('rateLimitPerMinute', 'rateLimitPerHour', 'rateLimitPerDay')
    @classmethod
    def validateRateLimits(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Rate limit must be non-negative")
        if v > 1000000:
            raise ValueError("Rate limit exceeds maximum allowed value")
        return v

    @field_validator('config')
    @classmethod
    def validateConfig(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        sanitized = {}
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Config keys must be strings")
            sanitized_key = validateStringInput(key, fieldName=f'config.{key}', maxLength=100)
            if isinstance(value, str):
                max_len = 10000 if key.lower() in ['bot_token', 'token', 'secret', 'api_key'] else 5000
                sanitized[sanitized_key] = value if len(value) <= max_len else value[:max_len]
            else:
                sanitized[sanitized_key] = value
        return sanitized

    def toEntity(self) -> TenantTelegramConfiguration:
        return TenantTelegramConfiguration(
            id=uuid4(),
            tenantId=self.tenantId,
            providerName=self.providerName,
            priority=self.priority,
            isActive=self.isActive,
            rateLimitPerMinute=self.rateLimitPerMinute,
            rateLimitPerHour=self.rateLimitPerHour,
            rateLimitPerDay=self.rateLimitPerDay,
            config=self.config,
        )


class TenantTelegramConfigurationResponseDTO(BaseModel):
    """Response DTO for tenant Telegram configurations."""
    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int
    isActive: bool = Field(alias="isActive")
    rateLimitPerMinute: int = Field(alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(alias="rateLimitPerDay")
    config: Dict[str, Any] = Field(default_factory=dict)
    createdAt: Optional[datetime] = Field(default=None, alias="createdAt")
    updatedAt: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)

    @classmethod
    def fromEntityWithRelations(cls, config: TenantTelegramConfiguration):
        return cls(
            id=config.id,
            tenantId=config.tenantId,
            providerName=config.providerName,
            priority=getattr(config, "priority", 1),
            isActive=config.isActive,
            rateLimitPerMinute=config.rateLimitPerMinute,
            rateLimitPerHour=config.rateLimitPerHour,
            rateLimitPerDay=config.rateLimitPerDay,
            config=getattr(config, "config", {}) or {},
            createdAt=getattr(config, "createdAt", None),
            updatedAt=getattr(config, "updatedAt", None),
        )


class TenantTelegramConfigurationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant Telegram configuration queries."""
    isActive: Optional[bool] = Field(None, alias="isActive", description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, alias="tenantId", description="Filter by tenant ID")
    providerName: Optional[str] = Field(None, alias="providerName", description="Filter by provider name")

    @field_validator('providerName')
    @classmethod
    def validateProviderName(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return validateStringInput(v, fieldName='providerName', maxLength=50)

    @field_validator('tenantId')
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        if v is None:
            return None
        return v
