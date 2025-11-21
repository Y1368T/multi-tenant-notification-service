from uuid import UUID
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.domain.value_objects.providers import EmailProvider
from notification_service.application.services.tenant_email_configuration import TenantEmailConfigurationService
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork


class EmailNotificationService:
    def __init__(self, email_config_service: TenantEmailConfigurationService, uow:IUnitOfWork):
        self.email_config_service = email_config_service
        self.uow = uow

    async def sendEmailNotification(self, tenant_id: UUID, email_notification: EmailNotification) -> bool:
        """Send an email notification using the tenant's email configuration.
        
        Args:
            tenant_id: Tenant identifier
            email_notification: EmailNotification entity to send

        Returns:
            True if the email was sent successfully, False otherwise
        """
        config = await self.email_config_service.get_configuration_by_tenant_id(tenant_id)
        if not config or not config.is_active:
            return False
        
        provider = EmailProvider(config.provider_name)
        is_healthy = await self.email_config_service.do_a_circuit_breaker_check(config, provider)
        if not is_healthy:
            return False
        
        handler = self.email_config_service._handlers.get(provider)
        if not handler:
            return False
        
        success = await handler.send_email(config, email_notification)
        return success

    async def getEmailNotifications(self, tenant_id: UUID) -> list[EmailNotification]:
        """Retrieve email notifications for a given tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of EmailNotification entities
        """
        async with self.uow:
            notifications = await self.uow.email_notifications.get_by_tenant_id(tenant_id)
            return notifications

    
    