from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.in_app.in_app_template import InAppTemplate


@dataclass
class InAppNotification:
    """Domain entity for in-app notifications"""
    
    id: UUID
    recipientUserId: str
    messageContent: str
    status: str = "unread"
    isRead: bool = False
    externalId: Optional[str] = None  # User ID in tenant's system for notification retrieval
    idempotencyKey: Optional[str] = None
    templateId: Optional[UUID] = None
    template: Optional[InAppTemplate] = None
    templateName: Optional[str] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
