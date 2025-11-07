from dataclasses import dataclass
from pydantic import ConfigDict,BaseModel

@dataclass
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

   
