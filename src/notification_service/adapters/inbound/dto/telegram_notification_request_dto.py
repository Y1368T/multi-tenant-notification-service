from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput
from uuid import UUID


class TelegramNotificationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for Telegram notification queries with custom filters."""
    status: Optional[str] = Field(None, description="Filter by notification status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    
    @field_validator('status')
    @classmethod
    def validateStatus(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        
        sanitized = validateStringInput(
            v,
            fieldName='status',
            maxLength=50
        )
        normalized = sanitized.lower()
        
        allowed_statuses = ["pending", "sent", "delivered", "failed", "cancelled"]
        if normalized not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        
        return normalized
    
    @field_validator('tenantId')
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        if v is None:
            return None
        return v
