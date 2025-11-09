from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class SMSNotification:
    """Domain entity for SMS notifications"""
    
    id: UUID
    recipient_number: str
    message_content: Dict[str, Any]
    status: str = "pending"
    idempotency_key: Optional[str] = None
    template_id: UUID = None
    templateName:Optional[str]=None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
