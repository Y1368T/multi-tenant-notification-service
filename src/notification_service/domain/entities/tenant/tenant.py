from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Tenant:
    """Domain entity for tenants"""
    
    id: UUID
    name: str
    prefix: str
    is_active: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    rate_limit_per_day: int = 10000
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)