from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate


@dataclass
class WhatsAppNotification:
    """Domain entity for WhatsApp notifications"""
    
    id: UUID
    recipientNumber: str
    messageContent: Dict[str, Any]
    status: str = "pending"
    isRead: bool = False
    externalId: Optional[str] = None  # User ID in tenant's system for notification retrieval
    idempotencyKey: Optional[str] = None
    templateId: UUID = None
    template: Optional[WhatsAppTemplate] = None
    templateName: Optional[str] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
