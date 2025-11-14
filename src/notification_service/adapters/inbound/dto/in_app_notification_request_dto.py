from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input
from uuid import UUID

class InAppNotificationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for in-app notification queries with custom filters."""
    status: Optional[str] = Field(None, description="Filter by notification status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate notification status filter."""
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
        allowed_statuses = ["unread", "read", "sent", "delivered", "failed", "cancelled"]
        if normalized not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        
        return normalized
    
    @field_validator('tenantId')
    @classmethod
    def validate_tenant_id(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        # UUID validation is handled by Pydantic automatically
        return v

