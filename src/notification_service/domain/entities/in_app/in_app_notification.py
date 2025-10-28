from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import UUID


@dataclass
class InAppNotification:
    """Domain entity for in-app notifications"""
    
    id: UUID
    recipient_user_id: str
    message_content: str
    status: str = "unread"
    idempotency_key: Optional[str] = None
    template_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
