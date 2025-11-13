from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class EmailOutbox:
    """Domain entity for email outbox"""
    
    id: UUID
    recipientEmail: str
    messageContent: Dict[str, Any]
    idempotencyKey: str
    templateId: Optional[UUID] = None
    retryCount: int = 0
    lastRetryAt: Optional[datetime] = None
    lastErrorMessage: Optional[str] = None
    nextRetryAt: Optional[datetime] = None
    providerAttempted: Optional[str] = None
    isSent: bool = False
    sentAt: Optional[datetime] = None
    status: str = "pending"
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
