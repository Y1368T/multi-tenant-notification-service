"""Direct email notification request DTO — no template required."""
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, field_validator

from notification_service.adapters.inbound.dto.direct_sms_request_dto import RecipientDTO


class DirectEmailRequestDTO(BaseModel):
    """
    Request body for ``POST /email-notifications/send-direct``.

    Send an email without a pre-defined template — the caller supplies the
    subject and body directly.

    Example::

        POST /email-notifications/send-direct?tenant_id=<uuid>
        {
          "recipient": {"address": "user@example.com", "externalId": "u-42"},
          "subject": "Your account has been credited",
          "message": "Dear customer, ETB 1,000 has been added to your account.",
          "idempotencyKey": "credit-txn-001"
        }
    """

    recipient: RecipientDTO
    subject: str
    message: str
    idempotencyKey: str = ""
    callbackUrl: Optional[str] = None
    callbackHeaders: Optional[Dict[str, str]] = None
    metadata: Optional[Dict] = None

    @field_validator("idempotencyKey", mode="before")
    @classmethod
    def default_idempotency_key(cls, v):
        return v or str(uuid.uuid4())
