from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID, uuid4
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput

class TenantInAppConfigurationRequestDto(BaseModel):
    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int
    isActive: bool = Field(default=True, alias="isActive")
    rateLimitPerMinute: int = Field(default=40, alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(default=600, alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(default=6000, alias="rateLimitPerDay")
    config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)

    @field_validator('providerName')
    @classmethod
    def validateProviderName(cls, v: str) -> str:
        """Validate provider name."""
        # allowedProviders = ["kifiya", "afromessage","fcm"]  # Update with actual in-app providers
        sanitized = validateStringInput(
            v,
            fieldName='providerName',
            maxLength=50
        )
        # if sanitized.lower() not in allowedProviders:
        #     raise ValueError(f"Provider must be one of: {', '.join(allowedProviders)}")
        # return sanitized.lower()
        return v
    
    @field_validator('priority')
    @classmethod
    def validatePriority(cls, v: int) -> int:
        """Validate priority (must be positive)."""
        if v < 1:
            raise ValueError("Priority must be at least 1")
        if v > 100:
            raise ValueError("Priority must be at most 100")
        return v
    
    @field_validator('rateLimitPerMinute', 'rateLimitPerHour', 'rateLimitPerDay')
    @classmethod
    def validateRateLimits(cls, v: int) -> int:
        """Validate rate limit values."""
        if v < 0:
            raise ValueError("Rate limit must be non-negative")
        if v > 1000000:  # Reasonable upper bound
            raise ValueError("Rate limit exceeds maximum allowed value")
        return v
    
    @field_validator('config')
    @classmethod
    def validateConfig(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        
        # Sanitize string values in config
        sanitizedConfig = {}
        for key, value in v.items():
            # Validate key
            if not isinstance(key, str):
                raise ValueError("Config keys must be strings")
            
            sanitizedKey = validateStringInput(
                key,
                fieldName=f'config.{key}',
                maxLength=100
            )
            
            # Sanitize value if it's a string
            if isinstance(value, str):
                # Allow longer values for config fields (e.g., private keys can be 2000+ chars)
                # Check for known long fields that need more space
                maxLen = 10000 if key in ['private_key', 'privateKey', 'certificate', 'cert', 'key'] else 5000
                
                # Skip SQL injection checking for encoded/sensitive fields (private keys, certificates, etc.)
                # These fields contain base64-encoded data that may accidentally match SQL patterns
                skipSqlCheck = key.lower() in [
                    'private_key', 'privatekey', 'private_key_id', 'privatekeyid',
                    'certificate', 'cert', 'key', 'token', 'secret', 'api_key', 'apikey',
                    'client_x509_cert_url', 'clientx509certurl', 'auth_provider_x509_cert_url'
                ]
                
                if skipSqlCheck:
                    # For sensitive fields, only validate length, skip SQL/XSS checks
                    if maxLen and len(value) > maxLen:
                        raise ValueError(f"config.{key} must be at most {maxLen} characters")
                    sanitizedValue = value  # Don't sanitize encoded data
                else:
                    sanitizedValue = validateStringInput(
                        value,
                        fieldName=f'config.{key}',
                        maxLength=maxLen
                    )
            else:
                sanitizedValue = value
            
            sanitizedConfig[sanitizedKey] = sanitizedValue
        
        return sanitizedConfig

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "TenantInAppConfigurationRequestDto":
        return cls(
            tenantId=data["tenantId"],
            providerName=data["providerName"],
            priority=int(data.get("priority", 1)),
            isActive=bool(data.get("isActive", True)),
            rateLimitPerMinute=int(data.get("rateLimitPerMinute", 40)),
            rateLimitPerHour=int(data.get("rateLimitPerHour", 600)),
            rateLimitPerDay=int(data.get("rateLimitPerDay", 6000)),
            config=data.get("config", {}),
        )

    def toEntity(self) -> TenantInAppConfiguration:
        return TenantInAppConfiguration(
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

class TenantInAppConfigurationResponseDTO(BaseModel):
    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    providerName: str = Field(alias="providerName")
    priority: int
    isActive: bool = Field(alias="isActive")
    rateLimitPerMinute: int = Field(alias="rateLimitPerMinute")
    rateLimitPerHour: int = Field(alias="rateLimitPerHour")
    rateLimitPerDay: int = Field(alias="rateLimitPerDay")
    createdAt: Optional[datetime] = Field(default=None, alias="createdAt")
    updatedAt: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)

    @classmethod
    def fromEntityWithRelations(cls, config: TenantInAppConfiguration):
        return cls(
            id=config.id,
            tenantId=config.tenantId,
            providerName=config.providerName,
            priority=getattr(config, "priority", 1),
            isActive=config.isActive,
            rateLimitPerMinute=config.rateLimitPerMinute,
            rateLimitPerHour=config.rateLimitPerHour,
            rateLimitPerDay=config.rateLimitPerDay,
            createdAt=getattr(config, "createdAt", None),
            updatedAt=getattr(config, "updatedAt", None),
        )


class TenantInAppConfigurationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant in-app configuration queries with custom filters."""
    isActive: Optional[bool] = Field(None, alias="isActive", description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, alias="tenantId", description="Filter by tenant ID")
    providerName: Optional[str] = Field(None, alias="providerName", description="Filter by provider name")
    
    @field_validator('providerName')
    @classmethod
    def validateProviderName(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider name filter."""
        if v is None or v == "":
            return None
        
        # Sanitize provider name
        sanitized = validateStringInput(
            v,
            fieldName='providerName',
            maxLength=50
        )
        
        # Validate against allowed providers
       # allowedProviders = ["kifiya", "afromessage","fcm"]  # Update with actual in-app providers
        normalized = sanitized.lower()
        # if normalized not in allowedProviders:
        #     raise ValueError(f"Provider name must be one of: {', '.join(allowedProviders)}")
        
        # return normalized
        return v
    
    @field_validator('tenantId')
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        # UUID validation is handled by Pydantic automatically
        return v

