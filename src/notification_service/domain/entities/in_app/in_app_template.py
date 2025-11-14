from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Dict, Optional

from notification_service.domain.entities.tenant.tenant import Tenant


@dataclass
class InAppTemplate:
    """Domain entity for in-app templates"""
    
    id: UUID
    templateName: str
    serviceName: str
    tenantId: UUID
    isActive: bool = True
    version: int = 1
    body: Dict[str, Dict[str, str]] = field(default_factory=dict)
    tenant: Optional[Tenant] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
