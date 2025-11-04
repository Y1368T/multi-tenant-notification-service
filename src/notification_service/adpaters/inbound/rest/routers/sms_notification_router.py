from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.application.services.sms_notification_service import SMSNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from uuid import UUID
from fastapi import Depends

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
    
    