from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class EmailNotification:
    """Domain entity for email notifications"""
    
    id: UUID
    recipient_email: str
    message_content: Dict[str, Any]
    status: str = "pending"
    idempotency_key: Optional[str] = None
    template_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
