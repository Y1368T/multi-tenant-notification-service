from dataclasses import dataclass
from pydantic import ConfigDict, BaseModel, field_validator
from uuid import UUID, uuid4
from typing import Optional, List
from datetime import datetime
import re

from pydantic import Field
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input

class TenantRequestDTO(BaseModel):
    name: str
    prefix: str
    isActive: bool = Field(alias="is_active")
    supportedChannels: list[str] = Field(alias="supported_channels")
    preferedCommunicationMethod: str = Field(alias="prefered_communication_method")
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Tenant A",
                "prefix": "TENANTA",
                "is_active": True,
                "supported_channels": ["sms", "email"],
                "prefered_communication_method": "rabbitmq"
            }
        })
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize tenant name."""
        return validate_string_input(
            v,
            field_name='name',
            max_length=255,
            min_length=1
        )
    
    @field_validator('prefix')
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """Validate and sanitize tenant prefix."""
        # Prefix should be uppercase alphanumeric
        sanitized = validate_string_input(
            v,
            field_name='prefix',
            max_length=50,
            min_length=1
        )
        # Ensure uppercase and alphanumeric only
        if not re.match(r'^[A-Z0-9_]+$', sanitized):
            raise ValueError("Prefix must contain only uppercase letters, numbers, and underscores")
        return sanitized.upper()
    
    @field_validator('preferedCommunicationMethod')
    @classmethod
    def validate_communication_method(cls, v: str) -> str:
        """Validate communication method."""
        allowed_methods = ["rest", "kafka", "rabbitmq", "grpc"]
        sanitized = validate_string_input(v, field_name='preferedCommunicationMethod')
        if sanitized.lower() not in allowed_methods:
            raise ValueError(f"Communication method must be one of: {', '.join(allowed_methods)}")
        return sanitized.lower()
    
    @field_validator('supportedChannels')
    @classmethod
    def validate_channels(cls, v: list[str]) -> list[str]:
        """Validate supported channels."""
        allowed_channels = ["sms", "email", "inapp", "whatsapp"]
        if not v:
            raise ValueError("At least one supported channel is required")
        
        sanitized_channels = []
        for channel in v:
            sanitized = validate_string_input(channel, field_name='supportedChannels')
            if sanitized.lower() not in allowed_channels:
                raise ValueError(f"Channel must be one of: {', '.join(allowed_channels)}")
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
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )


class TenantFilterDTO(PaginatedRequestDTO):
    """Filter DTO for tenant queries with custom filters."""
    status: Optional[str] = Field(None, description="Filter by tenant status")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status filter."""
        if v is None or v == "":
            return None
        
        # Sanitize status value
        sanitized = validate_string_input(
            v,
            field_name='status',
            max_length=50
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
    isActive: bool = Field(alias="is_active")
    supportedChannels: list[str] = Field(default_factory=list, alias="supported_channels")
    preferedCommunicationMethod: Optional[str] = Field(default=None, alias="prefered_communication_method")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
   
    @classmethod
    def fromEntityWithRelations(cls, tenant):
        return cls(
            id=tenant.id,
            name=tenant.name,
            prefix=tenant.prefix,
            isActive=getattr(tenant, "isActive", True),
            supportedChannels=getattr(tenant, "supportedChannels", None) or [],
            preferedCommunicationMethod=getattr(tenant, "preferedCommunicationMethod", None)
        )
