"""Email outbox REST controller."""
import logging
from uuid import UUID

from fastapi import Depends
from qena_shared_lib.http import ControllerBase, get, post, api_controller

from notification_service.application.services.email_outbox_service import EmailOutboxService
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.email_outbox_dto import (
    EmailOutboxResponseDTO,
    EmailOutboxFilterDTO,
)

logger = logging.getLogger(__name__)


@api_controller(prefix="/email-outboxes", tags=["Email Outbox"])
class EmailOutboxController(ControllerBase):
    """Controller for email outbox operations."""

    def __init__(self, emailOutboxService: EmailOutboxService = Depends()):
        self.emailOutboxService = emailOutboxService

    @get("/get", response_model=PaginatedResponseDTO[EmailOutboxResponseDTO])
    async def get(
        self, params: EmailOutboxFilterDTO = Depends()
    ) -> PaginatedResponseDTO[EmailOutboxResponseDTO]:
        """Get Email outbox entries by filters."""
        paginated_request = self.emailOutboxService._build_paginated_request(params)
        result = await self.emailOutboxService.get(paginated_request)
        return result

    @post("/retry", response_model=EmailOutboxResponseDTO)
    async def retry(self, outbox_id: UUID) -> EmailOutboxResponseDTO:
        """Retry a failed email outbox message."""
        result = await self.emailOutboxService.retry(outbox_id)
        return result
