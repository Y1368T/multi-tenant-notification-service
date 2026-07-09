from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID
from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate


@dataclass
class WhatsAppOutbox:
    """Domain entity for WhatsApp outbox"""
    
    id: UUID
    recipientNumber: str
    messageContent: str
    idempotencyKey: str
    templateId: Optional[UUID] = None
    template: Optional[WhatsAppTemplate] = None
    retryCount: int = 0
    lastRetryAt: Optional[datetime] = None
    lastErrorMessage: Optional[str] = None
    nextRetryAt: Optional[datetime] = None
    providerAttempted: Optional[str] = None
    isSent: bool = False
    sentAt: Optional[datetime] = None
    status: str = "pending"
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
