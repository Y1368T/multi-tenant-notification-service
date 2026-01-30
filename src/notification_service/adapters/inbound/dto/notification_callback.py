"""
Notification callback payload DTO.
Used for webhook callbacks to calling services.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class NotificationCallbackPayload:
    """
    Payload sent to callback URLs when notification status changes.
    
    Used for:
    - Immediate mode: Called after processing (success or failure)
    - Fire-and-forget mode: Called after final status (sent or permanently_failed)
    """
    idempotencyKey: str
    status: str  # "sent", "failed", "permanently_failed"
    channel: str  # "sms", "email", "inapp"
    recipient: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notificationId: Optional[str] = None
    errorMessage: Optional[str] = None
    retryCount: Optional[int] = None
    
    def toDict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "idempotencyKey": self.idempotencyKey,
            "status": self.status,
            "channel": self.channel,
            "recipient": self.recipient,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        }
        if self.notificationId:
            result["notificationId"] = self.notificationId
        if self.errorMessage:
            result["errorMessage"] = self.errorMessage
        if self.retryCount is not None:
            result["retryCount"] = self.retryCount
        return result

