"""Direct SMS notification request DTO — no template required."""
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, field_validator


class RecipientDTO(BaseModel):
    """A single notification recipient."""

    address: str
    externalId: Optional[str] = None


class DirectSMSRequestDTO(BaseModel):
    """
    Request body for ``POST /sms-notifications/send-direct``.

    Send an SMS without a pre-defined template — the caller supplies the
    final message content directly.

    Example::

        POST /sms-notifications/send-direct?tenant_id=<uuid>
        {
          "recipients": [{"address": "+251912345678"}],
          "message": "Your OTP is 123456. Valid for 5 minutes.",
          "idempotencyKey": "otp-txn-001",
          "callbackUrl": "https://myservice.internal/webhook",
          "callbackHeaders": {"Authorization": "Bearer token"}
        }
    """

    recipients: List[RecipientDTO]
    message: str
    idempotencyKey: str = ""
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    metadata: Optional[Dict] = None

    @field_validator("idempotencyKey", mode="before")
    @classmethod
    def default_idempotency_key(cls, v):
        return v or str(uuid.uuid4())
