from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class TenantSMSConfiguration:
    """Domain entity for tenant SMS configurations"""
    
    id: UUID
    tenant_id: UUID
    provider_name: str
    priroty: int=1
    is_active: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500
    rate_limit_per_day: int = 5000
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)