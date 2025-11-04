from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
@dataclass
class TenantInAppConfiguration:
    
    id: UUID
    tenant_id: UUID
    provider_name: str
    priority: int = 1
    is_active: bool = True
    rate_limit_per_minute: int = 40
    rate_limit_per_hour: int = 600
    rate_limit_per_day: int = 6000
    config: Dict[str, Any] = field(default_factory=dict)