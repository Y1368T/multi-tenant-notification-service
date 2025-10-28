from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class TenantEmailConfiguration:
    """Domain entity for tenant email configurations"""
    
    id: UUID
    tenant_id: UUID
    provider_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    is_active: bool = True
    rate_limit_per_minute: int = 50
    rate_limit_per_hour: int = 800
    rate_limit_per_day: int = 8000
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
