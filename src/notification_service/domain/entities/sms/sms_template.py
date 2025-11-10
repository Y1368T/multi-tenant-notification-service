from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.tenant.tenant import Tenant


@dataclass
class SmsTemplate:
    """Domain entity for SMS templates"""
    
    id: UUID
    tenant_id: UUID
    template_name: str
    service_name: str
    is_active: bool = True
    version: int = 1
    
    content: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tenant: Optional[Tenant] = None
