from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
from datetime import datetime
from pytz import timezone
@dataclass
class TenantInAppConfiguration:
    
    id: UUID
    tenantId: UUID
    providerName: str
    priority: int = 1
    isActive: bool = True
    rateLimitPerMinute: int = 40
    rateLimitPerHour: int = 600
    rateLimitPerDay: int = 6000
    config: Dict[str, Any] = field(default_factory=dict)
    createdAt: datetime = field(default_factory=datetime.now(timezone.utc))
    updatedAt: datetime = field(default_factory=datetime.now(timezone.utc))