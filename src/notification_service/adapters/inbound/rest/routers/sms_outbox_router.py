from qena_shared_lib.http import api_controller, ControllerBase, get, post
from fastapi import Depends, Query
from uuid import UUID
from notification_service.application.services.sms_outbox_service import SMSOutboxService
from notification_service.adapters.inbound.dto.sms_outbox_response_dto import SMSOutboxResponseDTO
from notification_service.adapters.inbound.dto.sms_outbox_filter_dto import SMSOutboxFilterDTO
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO

@api_controller(prefix="/sms-outboxes", tags=["SMS Outboxes"])
class SMSOutboxController(ControllerBase):
    def __init__(self, smsOutboxService: SMSOutboxService = Depends()):
        self.smsOutboxService = smsOutboxService
    
    @get("/get", response_model=PaginatedResponseDTO[SMSOutboxResponseDTO])
    async def get(self, params: SMSOutboxFilterDTO = Depends()) -> PaginatedResponseDTO[SMSOutboxResponseDTO]:
        """Get SMS outboxes by filters.
        
        Supports filtering by:
        - templateName
        - serviceName (through template)
        - recipientNumber
        - status
        - tenantId (through template)
        """
        paginated_request = self.smsOutboxService._build_paginated_request(params)
        result = await self.smsOutboxService.get(paginated_request)
        return result
    
    @post("/retry", response_model=SMSOutboxResponseDTO)
    async def retry(self, outbox_id: UUID = Query(..., description="ID of the outbox message to retry")) -> SMSOutboxResponseDTO:
        """Retry a failed SMS outbox message.
        
        Resets the retry count and status to allow the message to be processed again.
        """
        result = await self.smsOutboxService.retry(outbox_id)
        return result
