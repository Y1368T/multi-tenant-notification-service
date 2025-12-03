"""
Notification response value object.
Contract for API responses to external systems.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass(frozen=True)
class ProviderTestResponse:
    """Response from testing a notification provider."""
    success: bool
    message: Optional[str] = None
@dataclass(frozen=True)
class DeliveryAttemptResponse:
    """Individual delivery attempt information."""
    attempt_number: int
    provider: str
    status: str
    attempted_at: datetime
    error_message: Optional[str] = None

@dataclass(frozen=True)
class NotifiationResponsePerRecipient:
    """
    Notification status per recipient.
    Used within bulk notification responses.
    """
    recipient: str
    status: str
    deliveredAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    success: bool = True
    errorMessage: Optional[str] = None
    message: Optional[str] = None
    notificationId: Optional[str] = None

@dataclass(frozen=True)
class NotificationResponse:
    """
    Notification status response.
    Returned by REST API when querying notification status.
    
    Example response:
    {
        "notificationId": "uuid-1234-5678",
        "tenantId": "tenant-uuid",
        "channel": "sms",
        "status": "delivered",
        "recipient": "+251912345678",
        "createdAt": "2024-01-15T10:30:00Z",
        "deliveredAt": "2024-01-15T10:30:05Z"
    }
    """
    tenantId: Optional[str]=None
    channel: Optional[str]=None
    success: bool=False
    message: Optional[str]=None
    errorMessage: Optional[str]=None
    recipientResponse: Optional[List[NotifiationResponsePerRecipient]]=None


@dataclass(frozen=True)
class BulkNotificationResponse:
    """
    Bulk notification submission response.
    Returned by REST API when submitting multiple notifications.
    
    Example response:
    {
        "batchId": "batch-uuid-1234",
        "totalSubmitted": 100,
        "successfulSubmissions": 98,
        "failedSubmissions": 2,
        "notificationIds": ["uuid-1", "uuid-2", ...],
        "failures": [
            {
                "recipient": "+251912345678",
                "reason": "Invalid phone number format"
            }
        ]
    }
    """
    batchId: str
    totalSubmitted: int
    successfulSubmissions: int
    failedSubmissions: int
    notificationIds: List[str]
    failures: List[Dict[str, str]] = field(default_factory=list)
    success: bool = True
    errorMessage: Optional[str] = None
    message: Optional[str] = None
