from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from uuid import UUID


@dataclass
class EmailTemplate:
    """Domain entity for email templates"""
    
    id: UUID
    template_name: str
    subject: str
    service_name: str
    tenant_id: UUID
    body_type: str = "html"  # 'html' or 'text'
    file_urls: Optional[str] = None
    is_active: bool = True
    version: int = 1
    body: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
