from qena_shared_lib.http import api_controller, ControllerBase, get, post
from fastapi import Depends, Query
from uuid import UUID
from notification_service.application.services.whatsapp_outbox_service import WhatsAppOutboxService
from notification_service.adapters.inbound.dto.whatsapp_outbox_response_dto import WhatsAppOutboxResponseDTO
from notification_service.adapters.inbound.dto.whatsapp_outbox_filter_dto import WhatsAppOutboxFilterDTO
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO

@api_controller(prefix="/whatsapp-outboxes", tags=["WhatsApp Outboxes"])
class WhatsAppOutboxController(ControllerBase):
    def __init__(self, whatsappOutboxService: WhatsAppOutboxService = Depends()):
        self.whatsappOutboxService = whatsappOutboxService
    
    @get("/get", response_model=PaginatedResponseDTO[WhatsAppOutboxResponseDTO])
    async def get(self, params: WhatsAppOutboxFilterDTO = Depends()) -> PaginatedResponseDTO[WhatsAppOutboxResponseDTO]:
        """Get WhatsApp outboxes by filters.
        
        Supports filtering by:
        - templateName
        - serviceName (through template)
        - recipientNumber
        - status
        - tenantId (through template)
        """
        paginated_request = self.whatsappOutboxService._build_paginated_request(params)
        result = await self.whatsappOutboxService.get(paginated_request)
        return result
    
    @post("/retry", response_model=WhatsAppOutboxResponseDTO)
    async def retry(self, outbox_id: UUID = Query(..., description="ID of the outbox message to retry")) -> WhatsAppOutboxResponseDTO:
        """Retry a failed WhatsApp outbox message.
        
        Resets the retry count and status to allow the message to be processed again.
        """
        result = await self.whatsappOutboxService.retry(outbox_id)
        return result
