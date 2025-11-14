from qena_shared_lib.http import api_controller, ControllerBase, get, post
from fastapi import Depends, Query
from uuid import UUID
from notification_service.application.services.in_app_outbox_service import InAppOutboxService
from notification_service.adapters.inbound.dto.in_app_outbox_response_dto import InAppOutboxResponseDTO
from notification_service.adapters.inbound.dto.in_app_outbox_filter_dto import InAppOutboxFilterDTO
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO

@api_controller(prefix="/in-app-outboxes", tags=["In-App Outboxes"])
class InAppOutboxController(ControllerBase):
    def __init__(self, inAppOutboxService: InAppOutboxService = Depends()):
        self.inAppOutboxService = inAppOutboxService
    
    @get("/get", response_model=PaginatedResponseDTO[InAppOutboxResponseDTO])
    async def get(self, params: InAppOutboxFilterDTO = Depends()) -> PaginatedResponseDTO[InAppOutboxResponseDTO]:
        """Get in-app outboxes by filters.
        
        Supports filtering by:
        - templateName
        - serviceName (through template)
        - recipientUserId
        - status
        - tenantId (through template)
        """
        paginated_request = self.inAppOutboxService._build_paginated_request(params)
        result = await self.inAppOutboxService.get(paginated_request)
        return result
    
    @post("/retry", response_model=InAppOutboxResponseDTO)
    async def retry(self, outbox_id: UUID = Query(..., description="ID of the outbox message to retry")) -> InAppOutboxResponseDTO:
        """Retry a failed in-app outbox message.
        
        Resets the retry count and status to allow the message to be processed again.
        """
        result = await self.inAppOutboxService.retry(outbox_id)
        return result

