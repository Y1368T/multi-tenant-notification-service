"""Tenant email configuration request DTOs."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional
from uuid import uuid4, UUID
from datetime import datetime

from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.shared.validators.input_validators import validateStringInput


class TenantEmailConfigurationRequestDto(BaseModel):
    """Request DTO for creating/updating tenant email configurations."""

    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int = Field(default=1, description="Provider priority (1 = highest)")
    isActive: bool = Field(default=True, alias="isActive")
    rateLimitPerMinute: int = Field(default=50, alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(default=800, alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(default=8000, alias="rateLimitPerDay")
    config: Dict[str, Any] = Field(description="Provider-specific configuration")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "tenantId": "123e4567-e89b-12d3-a456-426614174000",
                "providerName": "smtp",
                "priority": 1,
                "isActive": True,
                "rateLimitPerMinute": 50,
                "rateLimitPerHour": 800,
                "rateLimitPerDay": 8000,
                "config": {
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "username": "your-email@gmail.com",
                    "password": "your-app-password",
                    "fromEmail": "noreply@yourcompany.com",
                    "fromName": "Your Company",
                    "useTls": True,
                    "useSsl": False,
                },
            }
        },
    )

    @field_validator("providerName")
    @classmethod
    def validateProviderName(cls, v: str) -> str:
        """Validate provider name."""
        sanitized = validateStringInput(v, fieldName="providerName", maxLength=50, minLength=1)
        normalized = sanitized.lower()

        allowed_providers = ["smtp", "sendgrid", "mailgun", "amazon_ses"]
        if normalized not in allowed_providers:
            raise ValueError(f"Provider must be one of: {', '.join(allowed_providers)}")

        return normalized

    @field_validator("priority")
    @classmethod
    def validatePriority(cls, v: int) -> int:
        """Validate priority."""
        if v < 1:
            raise ValueError("Priority must be at least 1")
        if v > 100:
            raise ValueError("Priority cannot exceed 100")
        return v

    @field_validator("rateLimitPerMinute", "rateLimitPerHour", "rateLimitPerDay")
    @classmethod
    def validateRateLimit(cls, v: int) -> int:
        """Validate rate limits."""
        if v < 0:
            raise ValueError("Rate limit cannot be negative")
        if v > 1000000:
            raise ValueError("Rate limit exceeds maximum allowed value")
        return v

    @field_validator("config")
    @classmethod
    def validateConfig(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary."""
        if not v:
            raise ValueError("Configuration cannot be empty")
        return v

    def toEntity(self) -> TenantEmailConfiguration:
        """Convert DTO to domain entity."""
        return TenantEmailConfiguration(
            id=uuid4(),
            tenantId=self.tenantId,
            providerName=self.providerName,
            priority=self.priority,
            isActive=self.isActive,
            rateLimitPerMinute=self.rateLimitPerMinute,
            rateLimitPerHour=self.rateLimitPerHour,
            rateLimitPerDay=self.rateLimitPerDay,
            config=self.config,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
        )


class TenantEmailConfigurationResponseDTO(BaseModel):
    """Response DTO for tenant email configurations."""

    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int
    isActive: bool = Field(alias="isActive")
    rateLimitPerMinute: int = Field(alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(alias="rateLimitPerDay")
    config: Dict[str, Any]
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")

    # Enriched fields
    tenantName: Optional[str] = Field(default=None, alias="tenantName")
    tenantPrefix: Optional[str] = Field(default=None, alias="tenantPrefix")

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=False
    )

    @classmethod
    def fromEntityWithRelations(cls, config: TenantEmailConfiguration):
        """Create DTO from entity with related data."""
        tenant_name = None
        tenant_prefix = None

        if hasattr(config, "tenant") and config.tenant:
            tenant_name = config.tenant.name or None
            tenant_prefix = config.tenant.prefix or None

        return cls(
            id=config.id,
            tenantId=config.tenantId,
            providerName=config.providerName,
            priority=config.priority,
            isActive=config.isActive,
            rateLimitPerMinute=config.rateLimitPerMinute,
            rateLimitPerHour=config.rateLimitPerHour,
            rateLimitPerDay=config.rateLimitPerDay,
            config=config.config,
            createdAt=config.createdAt,
            updatedAt=config.updatedAt,
            tenantName=tenant_name,
            tenantPrefix=tenant_prefix,
        )


class TenantEmailConfigurationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant email configuration queries."""

    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    providerName: Optional[str] = Field(None, description="Filter by provider name")
    isActive: Optional[bool] = Field(None, description="Filter by active status")

    @field_validator("tenantId")
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        return v

    @field_validator("providerName")
    @classmethod
    def validateProviderName(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider name filter."""
        if v is None or v == "":
            return None
        return validateStringInput(v, fieldName="providerName", maxLength=50)
