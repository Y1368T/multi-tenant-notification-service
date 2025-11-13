from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class TenantSMSConfiguration:
    """Domain entity for tenant SMS configurations"""
    
    id: UUID
    tenantId: UUID
    providerName: str
    priroty: int=1
    isActive: bool = True
    rateLimitPerMinute: int = 30
    rateLimitPerHour: int = 500
    rateLimitPerDay: int = 5000
    config: Dict[str, Any] = field(default_factory=dict)
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)