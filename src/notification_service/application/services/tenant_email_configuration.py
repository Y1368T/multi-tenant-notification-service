from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.domain.value_objects.providers import EmailProvider
from uuid import UUID
from notification_service.infrastructure.providers.email.smtp_email_sender import SmtpEmailSender
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
class TenantEmailConfigurationService:
    def __init__(self, uow:IUnitOfWork, email_provider:SmtpEmailSender):
        self.uow = uow
        self._handlers = {
            EmailProvider.SENDGRID: email_provider
        }
    
    async def get_configuration_by_tenant_id(self, tenant_id: UUID) -> TenantEmailConfiguration:
        """Retrieve email configuration for a given tenant.
        
        Args:
            tenant_id: Tenant identifier
        Returns:
            TenantEmailConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.email_configurations.get_by_tenant_id(tenant_id)
            return config
    async def create_configuration(self, config: TenantEmailConfiguration) -> TenantEmailConfiguration:
        """Create a new email configuration for a tenant.
        
        Args:
            config: TenantEmailConfiguration entity to create
        Returns:
            Created TenantEmailConfiguration entity
        """
        async with self.uow:
            created_config = await self.uow.email_configurations.add(config)
            await self.uow.commit()
            return created_config
    async def update_configuration(self, config: TenantEmailConfiguration) -> TenantEmailConfiguration:
        """Update an existing email configuration for a tenant.
        
        Args:
            config: TenantEmailConfiguration entity with updated values

        Returns:
            Updated TenantEmailConfiguration entity
        """
        async with self.uow:
            updated_config = await self.uow.email_configurations.update(config)
            await self.uow.commit()
            return updated_config
    async def delete_configuration(self, config_id: UUID) -> None:
        """Delete an existing email configuration for a tenant.
        
        Args:
            config_id: TenantEmailConfiguration identifier
        """
        async with self.uow:
            await self.uow.email_configurations.delete(config_id)   
    async def do_a_circuit_breaker_check(self, config: TenantEmailConfiguration, provider: EmailProvider) -> bool:
        """Perform a circuit breaker check for email configurations.
        
        Returns:
            True if the provider is healthy, False otherwise
        """
        # Placeholder implementation for circuit breaker logic
        
        match provider:
            case EmailProvider.SENDGRID:
                # Implement SendGrid-specific circuit breaker logic
                
                pass
        return True
    