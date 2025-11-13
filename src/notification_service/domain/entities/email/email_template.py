from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from uuid import UUID


@dataclass
class EmailTemplate:
    """Domain entity for email templates"""
    
    id: UUID
    templateName: str
    subject: str
    serviceName: str
    tenantId: UUID
    bodyType: str = "html"  # 'html' or 'text'
    fileUrls: Optional[str] = None
    isActive: bool = True
    version: int = 1
    body: Dict[str, str] = field(default_factory=dict)
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
