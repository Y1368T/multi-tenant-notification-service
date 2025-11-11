from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import UUID


@dataclass
class InAppNotification:
    """Domain entity for in-app notifications"""
    
    id: UUID
    recipientUserId: str
    messageContent: str
    status: str = "unread"
    idempotencyKey: Optional[str] = None
    templateId: Optional[UUID] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
