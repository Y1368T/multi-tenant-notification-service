from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.in_app_notification_service import InAppNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.in_app_notification_response_dto import InAppNotificationResponseDTO
from notification_service.adapters.inbound.dto.in_app_notification_request_dto import InAppNotificationFilterDTO
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
# We have stopped using basecrudrouter because InAppNotification can't be updated and created using a rest request
# so we are using controllerbase instead of basecrudrouter and this controller will only have get and send endpoints 

@api_controller(prefix="/in-app-notifications", tags=["In-App Notifications"])
class InAppNotificationController(ControllerBase):
    
    def __init__(self, inAppNotificationService: InAppNotificationService = Depends()):
        self.inAppNotificationService = inAppNotificationService
        
    
    
    @get("/get", response_model=PaginatedResponseDTO[InAppNotificationResponseDTO])
    async def get(self, params: InAppNotificationFilterDTO = Depends()) -> PaginatedResponseDTO[InAppNotificationResponseDTO]:
        """Get in-app notifications by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.inAppNotificationService._build_paginated_request(params)
        result = await self.inAppNotificationService.get(paginated_request)
        return result
    
   
    
    # Custom endpoints (not standard CRUD)
    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send in-app notification (custom endpoint)."""
        result = await self.inAppNotificationService.prepareAndSendInApp(tenant_id, requestDto)
        return result

