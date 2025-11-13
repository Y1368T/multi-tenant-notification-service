from dataclasses import dataclass
from pydantic import ConfigDict,BaseModel
from uuid import UUID, uuid4
from typing import Optional,List
from datetime import datetime

from pydantic import Field
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO

class TenantRequestDTO(BaseModel):
    name: str
    prefix: str
    isActive: bool = Field(alias="is_active")
    supportedChannels: list[str] = Field(alias="supported_channels")
    preferedCommunicationMethod: str = Field(alias="prefered_communication_method")
    model_config=ConfigDict(
        from_attributes = True,
        populate_by_name=True,
        json_schema_extra = {
            "example": {
                "name": "Tenant A",
                "prefix": "TENANTA",
                "is_active": True,
                "supported_channels":["sms","email"],
                "prefered_communication_method":"rabbitmq"
            }
        })
    
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
