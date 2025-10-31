from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Dict


@dataclass
class InAppTemplate:
    """Domain entity for in-app templates"""
    
    id: UUID
    template_name: str
    service_name: str
    tenant_id: UUID
    is_active: bool = True
    version: int = 1
    body: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
