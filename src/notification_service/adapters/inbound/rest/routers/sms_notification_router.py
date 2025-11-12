from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adapters.inbound.dto.sms_notification_request_dto import SMSNotificationFilterDTO
from notification_service.adapters.inbound.rest.routers.base_crud_router import BaseCRUDRouter
from notification_service.shared.exceptions.application_exceptions import ApplicationException
from uuid import UUID
from typing import Optional, List, Dict, Any
from fastapi import Depends, Query
import logging

logger = logging.getLogger(__name__)

@api_controller(prefix="/sms-notifications", tags=["SMS Notifications"])
class SMSNotificationController(BaseCRUDRouter[SMSNotification, SMSNotificationFilterDTO, SMSNotificationResponseDTO, SMSNotificationService]):
    
    def __init__(self, smsNotificationService: SMSNotificationService = Depends()):
        super().__init__(
            service=smsNotificationService,
            prefix="/sms-notifications",
            tags=["SMS Notifications"],
            request_dto_class=SMSNotificationFilterDTO,
            response_dto_class=SMSNotificationResponseDTO,
            entity_class=SMSNotification,
            create_dto_class=None  # SMS notifications are created via send endpoint, not standard create
        )
        self.smsNotificationService = smsNotificationService
        
    def _extract_custom_filters(self, params: SMSNotificationFilterDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        return filters
    
    def _build_paginated_request(self, params: SMSNotificationFilterDTO) -> PaginatedRequest:
        """Build PaginatedRequest for SMS notifications."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            root_filters['id'] = params.id
        if hasattr(params, 'tenantId') and params.tenantId:
                tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                root_filters['tenantId'] = tenant_id_value
        custom_filters = self.service._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Build related filters
        related_filters: List[RelatedFilter] = []
        if hasattr(params, 'tenantId') and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                )
            )
        # Build and return PaginatedRequest
        paginated_request = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=["recipientNumber","template.templateName","template.tenant.name","template.tenant.prefix"],
            filters=root_filters,
            relatedFilters=related_filters
        )
        return paginated_request
    @get("/get")
    async def get(self, params: SMSNotificationFilterDTO = Depends()):
        """Get SMS notifications by filters."""
        try:
            paginated_request = self._build_paginated_request(params)
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    # Custom endpoints (not standard CRUD)
    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send SMS notification (custom endpoint)."""
        result = await self.smsNotificationService.prepareAndSendSms(tenant_id, requestDto)
        return result
    