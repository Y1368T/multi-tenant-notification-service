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
    notification_id: Optional[str]=None
    tenant_id: Optional[str]=None
    channel: Optional[str]=None
    status: Optional[str]=None
    recipients: Optional[List[str]]=None # List of Phone/Email/DeviceToken addresses
    created_at: Optional[datetime]=None
    delivered_at: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None
    message: Optional[str] = None


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
    batch_id: str
    total_submitted: int
    successful_submissions: int
    failed_submissions: int
    notification_ids: List[str]
    failures: List[Dict[str, str]] = field(default_factory=list)
