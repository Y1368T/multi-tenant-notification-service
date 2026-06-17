"""Email notification REST controller."""
import logging
from uuid import UUID
from typing import Dict, Any, List

from fastapi import Depends
from qena_shared_lib.http import ControllerBase, get, post, api_controller

from notification_service.application.services.email_notification_service import EmailNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest, Recipient
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.email_notification_response_dto import EmailNotificationResponseDTO
from notification_service.adapters.inbound.dto.email_notification_request_dto import EmailNotificationFilterDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
from notification_service.adapters.inbound.dto.bulk_notification_request_dto import BulkNotificationRequestDTO
from notification_service.adapters.inbound.dto.direct_email_request_dto import DirectEmailRequestDTO

logger = logging.getLogger(__name__)


@api_controller(prefix="/email-notifications", tags=["Email Notifications"])
class EmailNotificationController(ControllerBase):
    """Controller for email notification operations."""

    def __init__(self, emailNotificationService: EmailNotificationService = Depends()):
        self.emailNotificationService = emailNotificationService

    @get("/get", response_model=PaginatedResponseDTO[EmailNotificationResponseDTO])
    async def get(
        self, params: EmailNotificationFilterDTO = Depends()
    ) -> PaginatedResponseDTO[EmailNotificationResponseDTO]:
        """Get Email notifications by filters."""
        # Build PaginatedRequest using service method
        paginated_request = self.emailNotificationService._build_paginated_request(params)
        result = await self.emailNotificationService.get(paginated_request)
        return result

    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send Email notification (custom endpoint)."""
        result = await self.emailNotificationService.prepareAndSendEmail(
            tenant_id, requestDto
        )
        return result

    @post("/send-bulk")
    async def sendBulk(self, tenant_id: UUID, requestDto: BulkNotificationRequestDTO):
        """Send multiple recipient-specific Email notifications in a single call.

        Each item in ``notifications`` is an independent notification with its
        own recipient, payload, and idempotency key. Valid items are processed
        even when others fail (partial success).
        """
        result = await self.emailNotificationService.sendBulkEmail(
            tenant_id, requestDto.notifications
        )
        return result

    @post("/send-direct")
    async def sendDirect(self, tenant_id: UUID, requestDto: DirectEmailRequestDTO):
        """Send a single email without a pre-defined template.

        The caller supplies the subject and message body directly — no template
        lookup or variable rendering is performed.
        """
        direct_request = DirectNotificationRequest(
            recipient=Recipient(address=requestDto.recipient.address, externalId=requestDto.recipient.externalId),
            message=requestDto.message,
            subject=requestDto.subject,
            idempotencyKey=requestDto.idempotencyKey,
            callbackUrl=requestDto.callbackUrl,
            callbackHeaders=requestDto.callbackHeaders,
            metadata=requestDto.metadata,
        )
        result = await self.emailNotificationService.prepareAndSendDirectEmail(tenant_id, direct_request)
        return result
