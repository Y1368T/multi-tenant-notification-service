from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class TenantEmailConfiguration:
    """Domain entity for tenant email configurations"""
    
    id: UUID
    tenantId: UUID
    providerName: str
    priority: int = 1
    isActive: bool = True
    rateLimitPerMinute: int = 50
    rateLimitPerHour: int = 800
    rateLimitPerDay: int = 8000
    config: Dict[str, Any] = field(default_factory=dict)
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
