from dataclasses import dataclass
from pydantic import ConfigDict, BaseModel, field_validator
from uuid import UUID, uuid4
from typing import Optional, List, Dict
from datetime import datetime
import re

from pydantic import Field
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput

class TenantRequestDTO(BaseModel):
    name: str
    prefix: str
    isActive: bool = Field(alias="isActive")
    supportedChannels: list[str] = Field(alias="supportedChannels")
    preferedCommunicationMethod: str = Field(alias="preferedCommunicationMethod")
    # Callback configuration for fire-and-forget mode
    callbackUrl: Optional[str] = Field(default=None, alias="callbackUrl", description="Webhook URL for notification status callbacks")
    callbackHeaders: Optional[Dict[str, str]] = Field(default=None, alias="callbackHeaders", description="Optional HTTP headers for callback authentication")
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Tenant A",
                "prefix": "TENANTA",
                "isActive": True,
                "supportedChannels": ["sms", "email"],
                "preferedCommunicationMethod": "rabbitmq",
                "callbackUrl": "https://service.internal/webhooks/notification",
                "callbackHeaders": {"Authorization": "Bearer secret-token"}
            }
        })
    
    @field_validator('name')
    @classmethod
    def validateName(cls, v: str) -> str:
        """Validate and sanitize tenant name."""
        return validateStringInput(
            v,
            fieldName='name',
            maxLength=255,
            minLength=1
        )
    
    @field_validator('prefix')
    @classmethod
    def validatePrefix(cls, v: str) -> str:
        """Validate and sanitize tenant prefix."""
        # Prefix should be uppercase alphanumeric
        sanitized = validateStringInput(
            v,
            fieldName='prefix',
            maxLength=50,
            minLength=1
        )
        # Ensure uppercase and alphanumeric only
        if not re.match(r'^[A-Z0-9_]+$', sanitized):
            raise ValueError("Prefix must contain only uppercase letters, numbers, and underscores")
        return sanitized.upper()
    
    @field_validator('preferedCommunicationMethod')
    @classmethod
    def validateCommunicationMethod(cls, v: str) -> str:
        """Validate communication method."""
        allowed_methods = ["rest", "kafka", "rabbitmq", "grpc"]
        sanitized = validateStringInput(v, fieldName='preferedCommunicationMethod')
        if sanitized.lower() not in allowed_methods:
            raise ValueError(f"Communication method must be one of: {', '.join(allowed_methods)}")
        return sanitized.lower()
    
    @field_validator('supportedChannels')
    @classmethod
    def validateChannels(cls, v: list[str]) -> list[str]:
        """Validate supported channels."""
        allowedChannels = ["sms", "email", "inapp", "whatsapp"]
        if not v:
            raise ValueError("At least one supported channel is required")
        
        sanitized_channels = []
        for channel in v:
            sanitized = validateStringInput(channel, fieldName='supportedChannels')
            if sanitized.lower() not in allowedChannels:
                raise ValueError(f"Channel must be one of: {', '.join(allowedChannels)}")
            sanitized_channels.append(sanitized.lower())
        
        return sanitized_channels
    
    def toEntity(self) -> Tenant:
        """Convert DTO to domain entity."""
        return Tenant(
            id=uuid4(),
            name=self.name,
            prefix=self.prefix,
            isActive=self.isActive,
            supportedChannels=self.supportedChannels,
            preferedCommunicationMethod=self.preferedCommunicationMethod,
            callbackUrl=self.callbackUrl,
            callbackHeaders=self.callbackHeaders,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )


class TenantFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant queries with custom filters."""
    status: Optional[str] = Field(None, description="Filter by tenant status")
    
    @field_validator('status')
    @classmethod
    def validateStatus(cls, v: Optional[str]) -> Optional[str]:
        """Validate status filter."""
        if v is None or v == "":
            return None
        
        # Sanitize status value
        sanitized = validateStringInput(
            v,
            fieldName='status',
            maxLength=50
        )
        
        # Normalize to lowercase
        normalized = sanitized.lower()
        
        # Validate against allowed status values
        allowed_statuses = ["active", "inactive", "pending", "suspended"]
        if normalized not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        
        return normalized


class TenantResponseDTO(BaseModel):
    id: UUID
    name: str
    prefix: str
    isActive: bool = Field(alias="isActive")
    supportedChannels: list[str] = Field(default_factory=list, alias="supportedChannels")
    preferedCommunicationMethod: Optional[str] = Field(default=None, alias="preferedCommunicationMethod")
    apiKeys: Optional[str] = Field(default=None, alias="apiKeys", description="API key for tenant authentication")
    callbackUrl: Optional[str] = Field(default=None, alias="callbackUrl", description="Webhook URL for notification status callbacks")
    callbackHeaders: Optional[Dict[str, str]] = Field(default=None, alias="callbackHeaders", description="HTTP headers for callback authentication")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
   
    @classmethod
    def fromEntityWithRelations(cls, tenant):
        return cls(
            id=tenant.id,
            name=tenant.name,
            prefix=tenant.prefix,
            isActive=getattr(tenant, "isActive", True),
            supportedChannels=getattr(tenant, "supportedChannels", None) or [],
            preferedCommunicationMethod=getattr(tenant, "preferedCommunicationMethod", None),
            apiKeys=getattr(tenant, "apiKeys", None) or "",
            callbackUrl=getattr(tenant, "callbackUrl", None),
            callbackHeaders=getattr(tenant, "callbackHeaders", None)
        )
