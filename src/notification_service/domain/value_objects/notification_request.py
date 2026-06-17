"""
Notification request value object.
Contract for external systems sending notifications via RabbitMQ/Kafka/REST.
"""
from dataclasses import dataclass, field
from importlib import metadata
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass(frozen=True)
class Recipient:
    """Individual recipient information."""
    address: str  # e.g., phone number, email, or Firebase token
    externalId: Optional[str] = None  # User ID in tenant's system for notification retrieval


@dataclass(frozen=True)
class NotificationRequest:
    """
    External notification request contract.
    This is what external systems send to RabbitMQ queues or REST API.
    
    Message queue format: notification.{channel}.{tenant-prefix}
    Example: notification.sms.qena
    
    JSON structure:
    {
        "serviceName": "payment-service",
        "recipient": {"address": "+251912345678"},
        "templateName": "account_balance",
        "payload": {"balance": "1000.00", "currency": "ETB"},
        "idempotencyKey": "unique-transaction-id-12345",
        "lang": "en",  # Optional, defaults to "en"
        "callbackUrl": "https://service.internal/webhook",  # Optional, for immediate mode
        "callbackHeaders": {"Authorization": "Bearer token"}  # Optional
    }
    """
    serviceName: str  # service identifier (e.g., "payment-service")
    recipient: Recipient
    templateName: str
    payload: Dict[str, Any]  # Template variables
    idempotencyKey: str = field(default_factory=lambda: str(uuid.uuid4()))
    lang: Optional[str] = None  # Optional, defaults to "en"
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    # Callback for immediate mode (per-request, optional)
    callbackUrl: Optional[str] = None  # Webhook URL for status notification
    callbackHeaders: Optional[Dict[str, str]] = None  # Optional auth headers for callback
    
    def __post_init__(self):
        """Validate request."""
        if not self.serviceName:
            raise ValueError("serviceName is required")
        if not self.recipient or not self.recipient.address:
            raise ValueError("recipient is required")
        if not self.templateName:
            raise ValueError("templateName is required")
        if not self.payload:
            raise ValueError("payload cannot be empty")
        if not self.idempotencyKey:
            raise ValueError("idempotencyKey is required")
    
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "NotificationRequest":
        """Create NotificationRequest from dictionary."""
        recipient_data = data.get("recipient")
        if recipient_data is None:
            recipient_data = data.get("recipient")

        if recipient_data is None:
            raise ValueError("recipient is required")

        if isinstance(recipient_data, list):
            if len(recipient_data) == 0:
                raise ValueError("recipient is required")
            if len(recipient_data) > 1:
                raise ValueError("Single notification request must contain exactly one recipient")
            recipient_data = recipient_data[0]

        if not isinstance(recipient_data, dict):
            raise ValueError("recipient must be an object")

        recipient = Recipient(
            address=recipient_data.get("address"),
            externalId=recipient_data.get("externalId") or recipient_data.get("external_id")
        )
        return cls(
            serviceName=data.get("serviceName") or data.get("service_name"),
            recipient=recipient,
            templateName=data.get("templateName") or data.get("template_name"),
            payload=data["payload"],
            idempotencyKey=data.get("idempotencyKey") or data.get("idempotency_key", str(uuid.uuid4())),
            lang=data.get("lang", "en"),
            metadata=data.get("metadata", {}),
            callbackUrl=data.get("callbackUrl") or data.get("callback_url"),
            callbackHeaders=data.get("callbackHeaders") or data.get("callback_headers")
        )
    
    def toDict(self) -> Dict[str, Any]:
        """Convert NotificationRequest to dictionary."""
        result = {
            "serviceName": self.serviceName,
            "recipient": {"address": self.recipient.address, "externalId": self.recipient.externalId},
            "templateName": self.templateName,
            "payload": self.payload,
            "idempotencyKey": self.idempotencyKey,
            "lang": self.lang,
            "metadata": self.metadata
        }
        if self.callbackUrl:
            result["callbackUrl"] = self.callbackUrl
        if self.callbackHeaders:
            result["callbackHeaders"] = self.callbackHeaders
        return result
