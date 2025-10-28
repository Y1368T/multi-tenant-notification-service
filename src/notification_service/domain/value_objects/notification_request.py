"""
Notification request value object.
Contract for external systems sending notifications via RabbitMQ/Kafka/REST.
"""
from dataclasses import dataclass, field
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
        "serviceName": "qena-bank",
        "recipients": [
            {"address": "+251912345678"},
            {"address": "+251923456789"}
        ],
        "templateName": "account_balance",
        "payload": {"balance": "1000.00", "currency": "ETB"},
        "idempotencyKey": "unique-transaction-id-12345",
        
    }
    """
    service_name: str  # Tenant identifier (e.g., "qena-bank")
    recipients: List[Recipient]
    template_name: str
    payload: Dict[str, Any]  # Template variables
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Validate request."""
        if not self.service_name:
            raise ValueError("serviceName is required")
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        if not self.template_name:
            raise ValueError("templateName is required")
        if not self.payload:
            raise ValueError("payload cannot be empty")
        if not self.idempotency_key:
            raise ValueError("idempotencyKey is required")
