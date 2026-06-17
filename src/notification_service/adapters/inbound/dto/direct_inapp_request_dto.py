"""Direct in-app notification request DTO — no template required."""
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, field_validator

from notification_service.adapters.inbound.dto.direct_sms_request_dto import RecipientDTO


class DirectInAppRequestDTO(BaseModel):
    """
    Request body for ``POST /in-app-notifications/send-direct``.

    Send an in-app (push) notification without a pre-defined template — the
    caller supplies the title and message body directly.

    Example::

        POST /in-app-notifications/send-direct?tenant_id=<uuid>
        {
          "recipient": {"address": "<fcm-token>", "externalId": "u-42"},
          "title": "Payment Received",
          "message": "ETB 500 has been credited to your wallet.",
          "idempotencyKey": "pay-rcv-001"
        }
    """

    recipient: RecipientDTO
    title: str
    message: str
    idempotencyKey: str = ""
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    metadata: Optional[Dict] = None

    @field_validator("idempotencyKey", mode="before")
    @classmethod
    def default_idempotency_key(cls, v):
        return v or str(uuid.uuid4())
