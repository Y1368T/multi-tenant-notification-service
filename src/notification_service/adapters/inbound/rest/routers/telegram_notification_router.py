from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.telegram_notification_service import TelegramNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.telegram_notification_response_dto import TelegramNotificationResponseDTO
from notification_service.adapters.inbound.dto.telegram_notification_request_dto import TelegramNotificationFilterDTO
from notification_service.adapters.inbound.dto.bulk_notification_request_dto import BulkNotificationRequestDTO
from typing import Dict, Any
from uuid import UUID
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)


@api_controller(prefix="/telegram-notifications", tags=["Telegram Notifications"])
class TelegramNotificationController(ControllerBase):
    """View and send Telegram notifications.

    Telegram notifications are **fire-and-forget**: once submitted the system
    dispatches the message and returns immediately. If delivery fails the
    record is moved to the outbox for automatic retry.

    - **GET /get** – query sent/pending notifications
    - **POST /send** – send a single notification via a template
    - **POST /send-bulk** – send multiple notifications in one call
    """

    def __init__(self, telegramNotificationService: TelegramNotificationService = Depends()):
        self.telegramNotificationService = telegramNotificationService

    @get("/get", response_model=PaginatedResponseDTO[TelegramNotificationResponseDTO])
    async def get(
        self, params: TelegramNotificationFilterDTO = Depends()
    ) -> PaginatedResponseDTO[TelegramNotificationResponseDTO]:
        """List Telegram notifications with optional filters.

        **Query parameters:**
        - `tenantId` – filter by tenant UUID (via template relationship)
        - `status` – filter by status (`pending`, `sent`, `failed`, etc.)
        - `search` – text search across recipientChatId and template fields
        - `page`, `pageSize`, `sortBy`, `sortDirection` – pagination controls
        """
        paginated_request = self.telegramNotificationService._build_paginated_request(params)
        return await self.telegramNotificationService.get(paginated_request)

    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send a Telegram notification using a pre-defined template.

        The `recipient.address` must be a **Telegram chat ID** (numeric string).
        Template variables are passed in the `variables` map.

        ```json
        {
          "templateName": "WelcomeMsg",
          "serviceName": "Onboarding",
          "language": "en",
          "recipient": { "address": "123456789", "externalId": "user_42" },
          "variables": { "userName": "Alice" },
          "idempotencyKey": "unique-key-here"
        }
        ```
        """
        return await self.telegramNotificationService.prepareAndSendTelegram(tenant_id, requestDto)

    @post("/send-bulk")
    async def sendBulk(self, tenant_id: UUID, requestDto: BulkNotificationRequestDTO):
        """Send multiple independent Telegram notifications in one call.

        Each item in `notifications` has its own recipient, payload, and
        idempotency key. Valid items are processed even when others fail
        (partial success is reported in the response).
        """
        return await self.telegramNotificationService.sendBulkTelegram(
            tenant_id, requestDto.notifications
        )
