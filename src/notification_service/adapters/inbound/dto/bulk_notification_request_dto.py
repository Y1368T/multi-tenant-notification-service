"""Bulk notification request DTO — shared by email, SMS, and in-app bulk endpoints."""
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

from notification_service.config.settings import settings
from notification_service.domain.value_objects.notification_request import NotificationRequest


class BulkNotificationRequestDTO(BaseModel):
    """
    Request body for bulk notification endpoints.

    Each item in ``notifications`` is an independent ``NotificationRequest`` that
    carries its own recipient(s), template, payload, and idempotency key —
    enabling recipient-specific content within a single HTTP call.

    Example::

        POST /email-notifications/send-bulk?tenant_id=<uuid>
        {
          "notifications": [
            {
              "serviceName": "payment-service",
              "recipients": [{"address": "alice@example.com", "externalId": "u-1"}],
              "templateName": "account_balance",
              "payload": {"balance": "1500.00", "currency": "ETB"},
              "idempotencyKey": "txn-001"
            },
            {
              "serviceName": "payment-service",
              "recipients": [{"address": "bob@example.com", "externalId": "u-2"}],
              "templateName": "account_balance",
              "payload": {"balance": "320.50", "currency": "ETB"},
              "idempotencyKey": "txn-002"
            }
          ]
        }
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    notifications: List[NotificationRequest]

    @field_validator("notifications")
    @classmethod
    def validate_notifications(cls, v: List[NotificationRequest]) -> List[NotificationRequest]:
        if len(v) < 1:
            raise ValueError("At least one notification is required")
        if len(v) > settings.bulk_max_notifications:
            raise ValueError(
                f"Bulk request cannot exceed {settings.bulk_max_notifications} notifications per call"
            )
        return v
