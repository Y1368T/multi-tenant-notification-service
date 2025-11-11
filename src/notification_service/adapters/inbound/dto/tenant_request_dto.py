from dataclasses import dataclass
from pydantic import ConfigDict,BaseModel
from uuid import UUID
from typing import Optional,List


from pydantic import Field

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
