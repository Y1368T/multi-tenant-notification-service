from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO

class InAppOutboxFilterDTO(PaginatedRequestDTO):
    """Filter DTO for in-app outbox queries with custom filters."""
    templateName: Optional[str] = Field(None, alias="templateName", description="Filter by template name")
    serviceName: Optional[str] = Field(None, alias="serviceName", description="Filter by service name")
    recipientUserId: Optional[str] = Field(None, alias="recipientUserId", description="Filter by recipient user ID")
    status: Optional[str] = Field(None, description="Filter by status")
    tenantId: Optional[UUID] = Field(None, alias="tenantId", description="Filter by tenant ID")
    
    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is None:
            return None
        allowed_statuses = ["pending", "sent", "failed", "retrying"]
        if v.lower() not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v.lower()

