from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from uuid import UUID
class SMSNotificationFilterDTO(PaginatedRequestDTO):
    """Filter DTO for SMS notification queries with custom filters."""
    status: Optional[str] = Field(None, description="Filter by notification status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
