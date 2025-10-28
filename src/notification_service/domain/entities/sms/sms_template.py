from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class SMSTemplate:
    """Domain entity for SMS templates"""
    
    id: UUID
    tenant_id: UUID
    template_name: str
    content: str
    service_name: str
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
