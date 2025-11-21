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
    address: str  # e.g., phone number or email


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
        "recipients": [
            {"address": "+251912345678"},
            {"address": "+251923456789"}
        ],
        "templateName": "account_balance",
        "payload": {"balance": "1000.00", "currency": "ETB"},
        "idempotencyKey": "unique-transaction-id-12345",
        "lang": "en"  # Optional, defaults to "en",
        
    }
    """
    serviceName: str  # service identifier (e.g., "payment-service")
    recipients: List[Recipient]
    templateName: str
    payload: Dict[str, Any]  # Template variables
    idempotencyKey: str = field(default_factory=lambda: str(uuid.uuid4()))
    lang: str = "en"  # Optional, defaults to "en"
    metadata:Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate request."""
        if not self.serviceName:
            raise ValueError("serviceName is required")
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        if not self.templateName:
            raise ValueError("templateName is required")
        if not self.payload:
            raise ValueError("payload cannot be empty")
        if not self.idempotencyKey:
            raise ValueError("idempotencyKey is required")
    
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "NotificationRequest":
        """Create NotificationRequest from dictionary."""
        recipients = [Recipient(**rec) for rec in data.get("recipients", [])]
        return cls(
            serviceName=data.get("serviceName") or data.get("service_name"),
            recipients=recipients,
            templateName=data.get("templateName") or data.get("template_name"),
            payload=data["payload"],
            idempotencyKey=data.get("idempotencyKey") or data.get("idempotency_key", str(uuid.uuid4())),
            lang=data.get("lang", "en"),
            metadata=data.get("metadata", {})
        )
    def toDict(self) -> Dict[str, Any]:
        """Convert NotificationRequest to dictionary."""
        return {
            "serviceName": self.serviceName,
            "recipients": [vars(recipient) for recipient in self.recipients],
            "templateName": self.templateName,
            "payload": self.payload,
            "idempotencyKey": self.idempotencyKey,
            "lang": self.lang,
            "metadata": self.metadata
        }
