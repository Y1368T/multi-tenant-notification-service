from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.telegram.telegram_template import TelegramTemplate


@dataclass
class TelegramNotification:
    """Domain entity for Telegram notifications"""
    
    id: UUID
    recipientChatId: str
    messageContent: Dict[str, Any]
    status: str = "pending"
    isRead: bool = False
    externalId: Optional[str] = None  # User ID in tenant's system for notification retrieval
    idempotencyKey: Optional[str] = None
    templateId: UUID = None
    template: Optional[TelegramTemplate] = None
    templateName: Optional[str] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
