from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from uuid import UUID
from typing import Optional
from fastapi import Depends, Query
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp,
)
import logging
logger = logging.getLogger(__name__)
@api_controller(prefix="/sms-notifications", tags=["SMS Notifications"])
class SMSNotificationController(ControllerBase):
    
    
    def __init__(self, sms_notification_service:SMSNotificationService = Depends()):
        self.sms_notification_service = sms_notification_service
        
    @post("/send")
    async def send_sms_notification(self, tenant_id: UUID, request_dto: NotificationRequest):
        result = await self.sms_notification_service.prepare_and_send_sms(tenant_id, request_dto)
        return result
    
    @get("/status/{notification_id}")
    async def get_sms_notification_status(self, notification_id: UUID):
        status = await self.sms_notification_service.get_notification_status(notification_id)
        return status
    
    @put("/update-status/{notification_id}")
    async def update_sms_notification_status(self, notification_id: UUID, status: str):
        updated_status = await self.sms_notification_service.update_notification_status(notification_id, status)
        return updated_status
    
    @delete("/delete/{notification_id}")
    async def delete_sms_notification(self, notification_id: UUID):
        await self.sms_notification_service.delete_notification(notification_id)
        return {"message": "SMS Notification deleted successfully"}
    
    
    
    @get("/all")
    async def get_all(
        self,
        status: Optional[str] = Query(None, description="Filter by notification status"),
        params: PaginatedRequestDTO = Depends(),
    ):
        default_search_fields = [
            "recipient_number",
            "template.template_name",
            "template.tenant.name",
            "template.tenant.prefix",
        ]

        root_filters = {"status": status} if status else {}
        related_filters: list[RelatedFilter] = []
        if params.tenant_id:
            related_filters.append(
                RelatedFilter(
                    relationship_path="template",
                    field="tenant_id",
                    op=FilterOp.EQ,
                    value=params.tenant_id
                )
            )

        req = PaginatedRequest(
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by or "created_at",
            sort_direction=params.sort_direction,
            search_text=params.search,
            search_fields=default_search_fields,
            filters=root_filters,
            related_filters=related_filters if related_filters else [],
        )

        result = await self.sms_notification_service.get_all_notifications_advanced(req)
        return result
        
    @get("/get_sms_by_tenant")
    async def get_all_query(
        self,
        params: PaginatedRequestDTO = Depends()
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        # Predefined search fields and related filters for SMS notifications

        logger.info(f"params: {params}")
        logger.info(f"params.tenant_id: {params.tenant_id}")
        default_search_fields = [
            "recipient_number",
            "template.template_name",
            "template.tenant.name",
            "template.tenant.prefix"
        ]
        default_related_filters: list[RelatedFilter] = []
        if params.tenant_id:
            default_related_filters.append(
                RelatedFilter(relationship_path="template", field="tenant_id", op="eq", value=params.tenant_id)
            )

        req = PaginatedRequest(
            page=params.page,
            page_size=params.page_size,
            sort_by="created_at",
            sort_direction=params.sort_direction,
            search=params.search,
            search_fields=default_search_fields,
            filters={},                    # add fixed root filters here if needed
            related_filters=default_related_filters
        )
        return await self.sms_notification_service.get_all_notifications_advanced(req)
        
    
    