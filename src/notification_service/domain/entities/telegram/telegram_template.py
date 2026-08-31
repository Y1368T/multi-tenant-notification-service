from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.tenant.tenant import Tenant


@dataclass
class TelegramTemplate:
    """Domain entity for Telegram templates"""
    
    id: UUID
    tenantId: UUID
    templateName: str
    serviceName: str
    isActive: bool = True
    version: int = 1
    
    content: Dict[str, str] = field(default_factory=dict)
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
    tenant: Optional[Tenant] = None
