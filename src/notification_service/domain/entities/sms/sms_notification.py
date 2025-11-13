from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from notification_service.domain.entities.sms.sms_template import SmsTemplate


@dataclass
class SMSNotification:
    """Domain entity for SMS notifications"""
    
    id: UUID
    recipientNumber: str
    messageContent: Dict[str, Any]
    status: str = "pending"
    idempotencyKey: Optional[str] = None
    templateId: UUID = None
    template:Optional[SmsTemplate]=None
    templateName:Optional[str]=None
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)
