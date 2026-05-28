"""
Direct notification request value object.
Used when sending a message without a pre-defined template.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import uuid

from notification_service.domain.value_objects.notification_request import Recipient


@dataclass(frozen=True)
class DirectNotificationRequest:
    """
    Template-free notification request.

    The caller supplies the final message content directly — no template lookup
    or variable rendering is performed.

    Fields
    ------
    recipients      : One or more recipients identified by their channel address
                      (phone number / email / FCM token) and an optional external id.
    message         : The raw message body to deliver as-is.
    idempotencyKey  : Caller-supplied unique key; auto-generated if omitted.
    subject         : Required for email channel; ignored by SMS and in-app.
    title           : Required for in-app channel; ignored by SMS and email.
    callbackUrl     : Optional webhook URL for asynchronous delivery status updates.
    callbackHeaders : Optional HTTP headers sent alongside the callback request.
    metadata        : Arbitrary key/value pairs forwarded to the underlying provider
                      (e.g. SMS shortcode selection).
    """

    recipients: List[Recipient]
    message: str
    idempotencyKey: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: Optional[str] = None
    title: Optional[str] = None
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        if not self.message or not self.message.strip():
            raise ValueError("message cannot be empty")
        if not self.idempotencyKey:
            raise ValueError("idempotencyKey is required")
