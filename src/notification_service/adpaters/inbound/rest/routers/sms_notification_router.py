from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.adpaters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adpaters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from uuid import UUID
from typing import Optional
from fastapi import Depends, Query

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
    
    @get("/get_sms_by_tenant/{tenantId}")
    async def getSmsByTenant(self,tenantId):
       result= await self.sms_notification_service.get_sms_notifications(tenantId)
       return result
    
    @get("/all")
    async def get_all(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
        search: Optional[str] = Query(None, description="Search in recipient number or message content"),
        status: Optional[str] = Query(None, description="Filter by notification status (e.g., pending, sent, failed)"),
        tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID")
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """
        Get all SMS notifications with pagination and filtering.
        
        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Number of items per page (default: 10, max: 100)
        - search: Search term for recipient number or message content
        - status: Filter by notification status
        - tenant_id: Filter by tenant ID
        
        Returns:
        - Paginated list of SMS notifications with enriched data including
          template_name, tenant_name, and tenant_prefix
        """
        result = await self.sms_notification_service.get_all_notifications(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            tenant_id=tenant_id
        )
        return result
        
    
    