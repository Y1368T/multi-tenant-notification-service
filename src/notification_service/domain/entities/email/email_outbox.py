from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class EmailOutbox:
    """Domain entity for email outbox"""
    
    id: UUID
    recipient_email: str
    message_content: Dict[str, Any]
    idempotency_key: str
    template_id: Optional[UUID] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    provider_attempted: Optional[str] = None
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
