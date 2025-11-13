from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID, uuid4
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input

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

    @field_validator('providerName')
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """Validate provider name."""
        allowed_providers = ["kifiya", "afromessage"]
        sanitized = validate_string_input(
            v,
            field_name='providerName',
            max_length=50
        )
        if sanitized.lower() not in allowed_providers:
            raise ValueError(f"Provider must be one of: {', '.join(allowed_providers)}")
        return sanitized.lower()
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority (must be positive)."""
        if v < 1:
            raise ValueError("Priority must be at least 1")
        if v > 100:
            raise ValueError("Priority must be at most 100")
        return v
    
    @field_validator('rateLimitPerMinute', 'rateLimitPerHour', 'rateLimitPerDay')
    @classmethod
    def validate_rate_limits(cls, v: int) -> int:
        """Validate rate limit values."""
        if v < 0:
            raise ValueError("Rate limit must be non-negative")
        if v > 1000000:  # Reasonable upper bound
            raise ValueError("Rate limit exceeds maximum allowed value")
        return v
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        
        # Sanitize string values in config
        sanitized_config = {}
        for key, value in v.items():
            # Validate key
            if not isinstance(key, str):
                raise ValueError("Config keys must be strings")
            
            sanitized_key = validate_string_input(
                key,
                field_name=f'config.{key}',
                max_length=100
            )
            
            # Sanitize value if it's a string
            if isinstance(value, str):
                sanitized_value = validate_string_input(
                    value,
                    field_name=f'config.{key}',
                    max_length=1000
                )
            else:
                sanitized_value = value
            
            sanitized_config[sanitized_key] = sanitized_value
        
        return sanitized_config

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
            priority=self.priority,
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
            priority=getattr(config, "priority", 1),
            isActive=config.isActive,
            rateLimitPerMinute=config.rateLimitPerMinute,
            rateLimitPerHour=config.rateLimitPerHour,
            rateLimitPerDay=config.rateLimitPerDay,
            config=getattr(config, "config", {}) or {},
            createdAt=getattr(config, "createdAt", None),
            updatedAt=getattr(config, "updatedAt", None),
        )


class TenantSMSConfigurationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant SMS configuration queries with custom filters."""
    isActive: Optional[bool] = Field(None, alias="is_active", description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, alias="tenant_id", description="Filter by tenant ID")
    providerName: Optional[str] = Field(None, alias="provider_name", description="Filter by provider name")
    
    @field_validator('providerName')
    @classmethod
    def validate_provider_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider name filter."""
        if v is None or v == "":
            return None
        
        # Sanitize provider name
        sanitized = validate_string_input(
            v,
            field_name='providerName',
            max_length=50
        )
        
        # Validate against allowed providers
        allowed_providers = ["kifiya", "afromessage"]
        normalized = sanitized.lower()
        if normalized not in allowed_providers:
            raise ValueError(f"Provider name must be one of: {', '.join(allowed_providers)}")
        
        return normalized
    
    @field_validator('tenantId')
    @classmethod
    def validate_tenant_id(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        # UUID validation is handled by Pydantic automatically
        return v