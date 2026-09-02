from fastapi import Depends
from uuid import UUID
from typing import Dict, Any
import logging

from notification_service.application.services.telegram_outbox_service import TelegramOutboxService
from notification_service.adapters.inbound.dto.telegram_outbox_response_dto import TelegramOutboxResponseDTO
from notification_service.adapters.inbound.dto.telegram_outbox_filter_dto import TelegramOutboxFilterDTO
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)


@api_controller(prefix="/telegram-outbox", tags=["Telegram Outbox"])
class TelegramOutboxController(ControllerBase):
    """Monitor and manage the Telegram outbox (retry queue).

    When a Telegram delivery fails the message is stored here for automatic
    background retries. This controller allows operators to inspect and
    manually trigger a re-attempt.

    - **GET /get** – list pending/failed outbox items
    - **POST /{id}/retry** – force an immediate retry for a specific item
    - **DELETE /{id}** – discard an outbox item without retrying
    """

    def __init__(self, telegramOutboxService: TelegramOutboxService = Depends()):
        self.telegramOutboxService = telegramOutboxService

    @get("/get", response_model=PaginatedResponseDTO[TelegramOutboxResponseDTO])
    async def get(
        self, params: TelegramOutboxFilterDTO = Depends()
    ) -> PaginatedResponseDTO[TelegramOutboxResponseDTO]:
        """List Telegram outbox items with optional filters.

        **Query parameters:**
        - `tenantId` – filter by tenant UUID (via template relationship)
        - `status` – filter by status (`pending`, `failed`, etc.)
        - `recipientChatId` – filter by exact chat ID
        - `templateName`, `serviceName` – filter by template metadata
        - `page`, `pageSize`, `sortBy`, `sortDirection` – pagination controls
        """
        paginated_request = self.telegramOutboxService._build_paginated_request(params)
        return await self.telegramOutboxService.get(paginated_request)

    @post("/{id}/retry", response_model=TelegramOutboxResponseDTO)
    async def retry(self, id: UUID) -> TelegramOutboxResponseDTO:
        """Force an immediate retry for a failed Telegram outbox item.

        This bypasses the background scheduler and attempts delivery right
        away using the tenant's active Telegram configuration.

        On **success** the outbox record is removed and a notification record
        is created in `telegramNotifications`.

        On **failure** the retry counter is incremented and the latest error
        message is stored for inspection.
        """
        return await self.telegramOutboxService.retry(id)

    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """Permanently discard a Telegram outbox item.

        Use this to remove a message that you no longer want the system to
        retry (e.g. if the recipient is invalid or the template was deleted).
        """
        await self.telegramOutboxService.delete(id)
        return {"message": "Telegram outbox item deleted successfully"}
