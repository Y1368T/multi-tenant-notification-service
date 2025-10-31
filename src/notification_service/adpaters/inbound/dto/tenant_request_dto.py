from dataclasses import dataclass

@dataclass
class TenantRequestDTO:
    tenant_id: str
    name: str
    prefix: str
    is_active: bool
    

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            tenant_id=data.get("tenant_id"),
            name=data.get("name"),
            prefix=data.get("prefix"),
            is_active=data.get("is_active", True)
        )
    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "prefix": self.prefix,
            "is_active": self.is_active
        }
