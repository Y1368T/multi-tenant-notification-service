from dataclasses import dataclass
from pydantic import ConfigDict,BaseModel

@dataclass
class TenantRequestDTO(BaseModel):
    name: str
    prefix: str
    is_active: bool
    model_config=ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "name": "Tenant A",
                "prefix": "TENANTA",
                "is_active": True
            }
        })

   
