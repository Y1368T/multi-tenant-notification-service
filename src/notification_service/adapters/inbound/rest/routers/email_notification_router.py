"""Email notification REST controller."""
import logging
from uuid import UUID
from typing import Dict, Any, List

from fastapi import Depends
from qena_shared_lib.http import ControllerBase, get, post, api_controller

from notification_service.application.services.email_notification_service import EmailNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.email_notification_response_dto import EmailNotificationResponseDTO
from notification_service.adapters.inbound.dto.email_notification_request_dto import EmailNotificationFilterDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest

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
