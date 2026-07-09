from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.whatsapp_notification_service import WhatsAppNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_request import Recipient
from notification_service.domain.entities.whatsapp.whatsapp_notification import WhatsAppNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.whatsapp_notification_response_dto import WhatsAppNotificationResponseDTO
from notification_service.adapters.inbound.dto.whatsapp_notification_request_dto import WhatsAppNotificationFilterDTO
from notification_service.adapters.inbound.dto.bulk_notification_request_dto import BulkNotificationRequestDTO
from notification_service.adapters.inbound.dto.direct_whatsapp_request_dto import DirectWhatsAppRequestDTO
from typing import Dict, Any, List
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    RelatedFilter,
    FilterOp
)
from uuid import UUID
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)
# we have stoped using basecrudrouter because we have WhatsAppNotification is can't be updated and created using a rest request
# so we are using controllerbase instead of basecrudrouter and we this controller will only have get and send endpoints 

@api_controller(prefix="/whatsapp-notifications", tags=["WhatsApp Notifications"])
class WhatsAppNotificationController(ControllerBase):
    
    def __init__(self, whatsappNotificationService: WhatsAppNotificationService = Depends()):
        self.whatsappNotificationService = whatsappNotificationService
       
    @get("/get", response_model=PaginatedResponseDTO[WhatsAppNotificationResponseDTO])
    async def get(self, params: WhatsAppNotificationFilterDTO = Depends()) -> PaginatedResponseDTO[WhatsAppNotificationResponseDTO]:
        """Get WhatsApp notifications by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.whatsappNotificationService._build_paginated_request(params)
        result = await self.whatsappNotificationService.get(paginated_request)
        return result
    
   
    
    # Custom endpoints (not standard CRUD)
    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send WhatsApp notification (custom endpoint)."""
        result = await self.whatsappNotificationService.prepareAndSendWhatsApp(tenant_id, requestDto)
        return result

    @post("/send-bulk")
    async def sendBulk(self, tenant_id: UUID, requestDto: BulkNotificationRequestDTO):
        """Send multiple recipient-specific WhatsApp notifications in a single call.

        Each item in ``notifications`` is an independent notification with its
        own recipient, payload, and idempotency key. Valid items are processed
        even when others fail (partial success).
        """
        result = await self.whastappNotificationService.sendBulkWhatsApp(
            tenant_id, requestDto.notifications
        )
        return result

    @post("/send-direct")
    async def sendDirect(self, tenant_id: UUID, requestDto: DirectWhatsAppRequestDTO):
        """Send a single WhatsApp without a pre-defined template.

        The caller supplies the final message content directly — no template
        lookup or variable rendering is performed.
        """
        direct_request = DirectNotificationRequest(
            recipient=Recipient(address=requestDto.recipient.address, externalId=requestDto.recipient.externalId),
            message=requestDto.message,
            idempotencyKey=requestDto.idempotencyKey,
            callbackUrl=requestDto.callbackUrl,
            callbackHeaders=requestDto.callbackHeaders,
            metadata=requestDto.metadata,
        )
        result = await self.whatsappNotificationService.prepareAndSendDirectWhatsApp(tenant_id, direct_request)
        return result
    