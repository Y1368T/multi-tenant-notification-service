from typing import Optional, Dict
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.providers import SMSProvider

class TenantSMSConfigurationService:


    def __init__(self, uow, ethio_service):
        self.uow = uow
        self._handlers = {
            SMSProvider.ETHIOTELECOM: ethio_service
        }

    async def get_configuration_by_tenant_id(self, tenant_id: UUID) -> TenantSMSConfiguration:
        """Retrieve SMS configuration for a given tenant.
        
        Args:
            tenant_id: Tenant identifier

        Returns:
            TenantSMSConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.sms_configurations.get_by_tenant_id(tenant_id)
            return config
    async def create_configuration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Create a new SMS configuration for a tenant.
        
        Args:
            config: TenantSMSConfiguration entity to create

        Returns:
            Created TenantSMSConfiguration entity
        """
        async with self.uow:
            created_config = await self.uow.sms_configurations.add(config)
            await self.uow.commit()
            return created_config
        
    async def update_configuration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Update an existing SMS configuration for a tenant.

        Args:
            config: TenantSMSConfiguration entity with updated values

        Returns:
            Updated TenantSMSConfiguration entity
        """
        async with self.uow:
            updated_config = await self.uow.sms_configurations.update(config)
            await self.uow.commit()
            return updated_config
        
    async def delete_configuration(self, config_id: UUID) -> None:
        """Delete an existing SMS configuration for a tenant.

        Args:
            config_id: TenantSMSConfiguration identifier
        """
        async with self.uow:
            await self.uow.sms_configurations.delete(config_id)
            await self.uow.commit()
            
    async def get_configuration_by_id(self, config_id: UUID) -> Optional[TenantSMSConfiguration]:
        """Retrieve SMS configuration by its ID.
        
        Args:
            config_id: TenantSMSConfiguration identifier

        Returns:
            TenantSMSConfiguration entity if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.sms_configurations.get_by_id(config_id)
            return config
        
    async def do_a_circuit_breaker_check(self, config: TenantSMSConfiguration, provider: SMSProvider) -> bool:
        """Perform a circuit breaker check for SMS configurations.
        
        Returns:
            bool: True if the circuit is closed, False if open
        """
        # Placeholder implementation for circuit breaker logic
        
        match provider:
            case SMSProvider.ETHIOTELECOM:
                # Implement EthioTelecom-specific circuit breaker logic
               return self._handlers[provider].circuit_breaker_check(config)
            case SMSProvider.AFROMESSAGE:
               return self._handlers[provider].circuit_breaker_check(config)
            case _:
                return False
        return False