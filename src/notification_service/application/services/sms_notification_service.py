from uuid import UUID
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
class SMSNotificationService:
    def __init__(self, uow:IUnitOfWork, process_message_use_case: ProcessMessageUseCase,message_router:IMessageHandler):
        self.uow = uow
        self.process_message_use_case = process_message_use_case
        self.message_router=message_router


    async def prepare_and_send_sms(self, tenant_id: UUID, message_data: NotificationRequest) -> NotificationResponse:
        """Prepare and send an SMS notification.

        Args:
            tenant_id: Tenant identifier
            message_data: Dictionary containing SMS message details
            """
        
        valid= self.process_message_use_case.validate_message(message=message_data,channel=NotificationChannel.SMS)
        if valid is None:
            return {"success": False, "error": "Validation failed"}
        
        if isinstance(valid, dict) and valid.get("success") is False:
            return valid
        tenant = None
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(tenant_id)
            
            if not tenant:
                return {"success": False, "error": "Tenant does not exist"}
            response= await self.message_router.do_route(NotificationChannel.SMS, tenant, message_data)
            return response
            
    
    async def get_sms_notifications(self, tenant_id):
        """Retrieve SMS notifications for a given tenant.

        Args:
            tenant_id: Tenant identifier
        Returns:
            List of SMSNotification entities
        """
        async with self.uow:
            notifications = await self.uow.sms_notifications.get_by_tenant_id(tenant_id)
            return notifications
        
