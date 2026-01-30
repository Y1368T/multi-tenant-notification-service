from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class EmailNotification:
    """Domain entity for email notifications"""
    
    id: UUID
    recipientEmail: str
    messageContent: Dict[str, Any]
    status: str = "pending"
    isRead: bool = False
    externalId: Optional[str] = None  # User ID in tenant's system for notification retrieval
    idempotencyKey: Optional[str] = None
    templateId: Optional[UUID] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
