from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_request import Recipient
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adapters.inbound.dto.sms_notification_request_dto import SMSNotificationFilterDTO
from notification_service.adapters.inbound.dto.bulk_notification_request_dto import BulkNotificationRequestDTO
from notification_service.adapters.inbound.dto.direct_sms_request_dto import DirectSMSRequestDTO
from typing import Dict, Any, List
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    RelatedFilter,
    FilterOp
)
from uuid import UUID
from fastapi import Depends, Request
from notification_service.adapters.inbound.dependencies import verify_tenant_access
import logging

logger = logging.getLogger(__name__)
# we have stoped using basecrudrouter because we have SMSNotification is can't be updated and created using a rest request
# so we are using controllerbase instead of basecrudrouter and we this controller will only have get and send endpoints 

@api_controller(prefix="/sms-notifications", tags=["SMS Notifications"])
class SMSNotificationController(ControllerBase):
    
    def __init__(self, smsNotificationService: SMSNotificationService = Depends()):
        self.smsNotificationService = smsNotificationService
       
    @get("/get", response_model=PaginatedResponseDTO[SMSNotificationResponseDTO])
    async def get(self, params: SMSNotificationFilterDTO = Depends()) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """Get SMS notifications by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.smsNotificationService._build_paginated_request(params)
        result = await self.smsNotificationService.get(paginated_request)
        return result
    
   
    
    # Custom endpoints (not standard CRUD)
    @post("/send", dependencies=[Depends(verify_tenant_access)])
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send SMS notification (custom endpoint)."""
        result = await self.smsNotificationService.prepareAndSendSms(tenant_id, requestDto)
        return result

    @post("/send-bulk", dependencies=[Depends(verify_tenant_access)])
    async def sendBulk(self, tenant_id: UUID, requestDto: BulkNotificationRequestDTO):
        """Send multiple recipient-specific SMS notifications in a single call.

        Each item in ``notifications`` is an independent notification with its
        own recipient, payload, and idempotency key. Valid items are processed
        even when others fail (partial success).
        """
        result = await self.smsNotificationService.sendBulkSms(
            tenant_id, requestDto.notifications
        )
        return result

    @post("/send-direct", dependencies=[Depends(verify_tenant_access)])
    async def sendDirect(self, tenant_id: UUID, requestDto: DirectSMSRequestDTO):
        """Send a single SMS without a pre-defined template.

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
        result = await self.smsNotificationService.prepareAndSendDirectSms(tenant_id, direct_request)
        return result
    