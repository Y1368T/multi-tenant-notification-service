
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Dict, Optional, Any

from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate


@dataclass
class InAppOutbox:
    """Domain entity for in-app outbox"""
    
    id: UUID
    templateId: UUID
    recipientUserId: str
    messageContent: Dict[str, Dict[str, str]]
    template: Optional[InAppTemplate] = None
    idempotencyKey: Optional[str] = None
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