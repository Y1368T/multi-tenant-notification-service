from uuid import UUID
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.value_objects.providers import SMSProvider

class SMSNotificationService:
    def __init__(self, uow, sms_provider):
        self.uow = uow
        self.sms_provider = sms_provider

    async def send_sms_notification(self, tenant_id: UUID, sms_notification: SMSNotification) -> bool:
        """Send an SMS notification using the SMS provider.

        Args:
            sms_notification: SMSNotification entity to send

        Returns:
            True if the SMS was sent successfully, False otherwise
        """
        config = await self.uow.sms_configurations.get_by_tenant_id(tenant_id)
        if not config or not config.is_active:
            return False
        
        provider = SMSProvider(config.provider_name)
        is_healthy = await self.sms_provider.do_a_circuit_breaker_check(config, provider)
        if not is_healthy:
            return False

        handler = self.sms_provider._handlers.get(provider)
        if not handler:
            return False

        success = await self.sms_provider.send_sms(config, sms_notification)
        return success
    
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
        
