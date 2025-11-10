from dataclasses import dataclass
from pydantic import ConfigDict,BaseModel
from uuid import UUID
from typing import Optional,List


class TenantRequestDTO(BaseModel):
    name: str
    prefix: str
    is_active: bool
    supported_channels: list[str]
    prefered_communication_method: str
    model_config=ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "name": "Tenant A",
                "prefix": "TENANTA",
                "is_active": True,
                "supported_channels":["sms","email"],
                "prefered_communication_method":"rabbitmq"
            }
        })


class TenantResponseDTO(BaseModel):
    id: UUID
    name: str
    prefix: str
    is_active: bool
    supported_channels: list[str] = []  # Default to empty list
    prefered_communication_method: Optional[str] = None  # Also make this optional
    
    model_config = ConfigDict(from_attributes=True)
   
    @classmethod
    def from_entity_with_relations(cls, tenant):
        return cls(
            id=tenant.id,
            name=tenant.name,
            prefix=tenant.prefix,
            is_active=getattr(tenant, "is_active", True),
            supported_channels=getattr(tenant, "supported_channels", None) or [],  # Handle None
            prefered_communication_method=getattr(tenant, "prefered_communication_method", None)
        )
