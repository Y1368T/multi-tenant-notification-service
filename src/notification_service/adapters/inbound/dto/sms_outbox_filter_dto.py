from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO

class SMSOutboxFilterDTO(PaginatedRequestDTO):
    """Filter DTO for SMS outbox queries with custom filters."""
    templateName: Optional[str] = Field(None, alias="template_name", description="Filter by template name")
    serviceName: Optional[str] = Field(None, alias="service_name", description="Filter by service name")
    recipientNumber: Optional[str] = Field(None, alias="recipient_number", description="Filter by recipient number")
    status: Optional[str] = Field(None, description="Filter by status")
    tenantId: Optional[UUID] = Field(None, alias="tenant_id", description="Filter by tenant ID")
    
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

