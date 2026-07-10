"""Direct WhatsApp notification request DTO — no template required."""
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, field_validator


class RecipientDTO(BaseModel):
    """A single notification recipient."""

    address: str
    externalId: Optional[str] = None


class DirectWhatsAppRequestDTO(BaseModel):
    """
    Request body for ``POST /whatsapp-notifications/send-direct``.

    Send an WhatsApp without a pre-defined template — the caller supplies the
    final message content directly.

    Example::

        POST /whatsapp-notifications/send-direct?tenant_id=<uuid>
        {
          "recipient": {"address": "+251912345678"},
          "message": "Your OTP is 123456. Valid for 5 minutes.",
          "idempotencyKey": "otp-txn-001",
          "callbackUrl": "https://myservice.internal/webhook",
          "callbackHeaders": {"Authorization": "Bearer token"}
        }
    """

    recipient: RecipientDTO
    message: str
    idempotencyKey: str = ""
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    metadata: Optional[Dict] = None

    @field_validator("idempotencyKey", mode="before")
    @classmethod
    def default_idempotency_key(cls, v):
        return v or str(uuid.uuid4())
