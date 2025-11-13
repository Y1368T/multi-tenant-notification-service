from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adapters.inbound.dto.sms_notification_request_dto import SMSNotificationFilterDTO
from uuid import UUID
from fastapi import Depends
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
    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send SMS notification (custom endpoint)."""
        result = await self.smsNotificationService.prepareAndSendSms(tenant_id, requestDto)
        return result
    