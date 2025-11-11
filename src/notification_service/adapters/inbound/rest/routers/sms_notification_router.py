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
    
    
    def __init__(self, smsNotificationService:SMSNotificationService = Depends()):
        self.smsNotificationService = smsNotificationService
        
    @post("/send")
    async def sendSmsNotification(self, tenant_id: UUID, requestDto: NotificationRequest):
        result = await self.smsNotificationService.prepareAndSendSms(tenant_id, requestDto)
        return result
    
    @get("/status/{notification_id}")
    async def getSmsNotificationStatus(self, notification_id: UUID):
        status = await self.smsNotificationService.getNotificationStatus(notification_id)
        return status
    
    @put("/update-status/{notification_id}")
    async def updateSmsNotificationStatus(self, notification_id: UUID, status: str):
        updatedStatus = await self.smsNotificationService.updateNotificationStatus(notification_id, status)
        return updatedStatus
    
    @delete("/delete/{notification_id}")
    async def deleteSmsNotification(self, notification_id: UUID):
        await self.smsNotificationService.deleteNotification(notification_id)
        return {"message": "SMS Notification deleted successfully"}
    
    
    
    @get("/all")
    async def getAll(
        self,
        status: Optional[str] = Query(None, description="Filter by notification status"),
        params: PaginatedRequestDTO = Depends(),
    ):
        defaultSearchFields = [
            "recipientNumber",
            "template.templateName",
            "template.tenant.name",
            "template.tenant.prefix",
        ]

        rootFilters = {"status": status} if status else {}
        relatedFilters: list[RelatedFilter] = []
        if params.tenantId:
            relatedFilters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=params.tenantId
                )
            )

        req = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=defaultSearchFields,
            filters=rootFilters,
            relatedFilters=relatedFilters if relatedFilters else [],
        )

        result = await self.smsNotificationService.getAllNotificationsAdvanced(req)
        return result
        
    @get("/get_sms_by_tenant")
    async def getAllQuery(
        self,
        params: PaginatedRequestDTO = Depends()
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        # Predefined search fields and related filters for SMS notifications

        logger.info(f"params: {params}")
        logger.info(f"params.tenantId: {params.tenantId}")
        defaultSearchFields = [
            "recipientNumber",
            "template.templateName",
            "template.tenant.name",
            "template.tenant.prefix"
        ]
        defaultRelatedFilters: list[RelatedFilter] = []
        if params.tenantId:
            defaultRelatedFilters.append(
                RelatedFilter(relationshipPath="template", field="tenantId", op="eq", value=params.tenantId)
            )

        req = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy="createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=defaultSearchFields,
            filters={},
            relatedFilters=defaultRelatedFilters
        )
        return await self.smsNotificationService.getAllNotificationsAdvanced(req)
        
    
    