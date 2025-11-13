from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import UUID


@dataclass
class SMSOutbox:
    """Domain entity for SMS outbox"""
    
    id: UUID
    recipientNumber: str
    messageContent: str
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
