from typing import List,Optional
from uuid import UUID
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.domain.interfaces import IUnitOfWork
from notification_service.Infrastructure.messaging.rabbitmq import RabbitMQConsumer
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer

class TenantService:
    def __init__(self, uow: IUnitOfWork,rabbitmq_consumer:IMessageConsumer):
        self.uow = uow
        self.rabbitmq_consumer=rabbitmq_consumer
    
        
        
    async def get_tenant_by_prefix(self, prefix: str ) -> Optional[Tenant]:
        """Retrieve tenant by its prefix.
        
        Args:
            prefix: Tenant prefix string
            
        Returns:
            Tenant entity if found, None otherwise
        """
        async with self.uow:
            tenant = await self.uow.tenants.get_tenant_by_prefix(prefix)
            return tenant
    async def list_all_tenants(self) -> List[Tenant]:
        """List all tenants in the system.
        
        Returns:
            List of Tenant entities
        """
        async with self.uow:
            tenants = await self.uow.tenants.list()
            return tenants
    async def create_tenant(self, tenant: Tenant) -> Tenant:
        """Create a new tenant.
        
        Args:
            tenant: Tenant entity to create
            
        Returns:
            Created Tenant entity with generated ID
        """
        async with self.uow:
            created_tenant: Tenant = await self.uow.tenants.add(tenant)
            await self.uow.commit()
            if(created_tenant.prefered_communication_method == "rabbitmq" and created_tenant.is_active and created_tenant.supported_channels and self.rabbitmq_consumer):
                # Additional logic for rabbitmq preferred communication method can be added here
                for channel in created_tenant.supported_channels:
                    queue_name = f"notification.{channel}.{created_tenant.prefix}"
                    # Here you might want to initialize or configure the queue for the tenant
                    await self.rabbitmq_consumer.ensure_queue_exists_and_subscribe(queue_name=queue_name,channel=channel)
                    pass
                
            return created_tenant
    async def update_tenant(self, tenant: Tenant) -> Tenant:
        """Update an existing tenant.
        
        Args:
            tenant: Tenant entity with updated values
            
        Returns:
            Updated Tenant entity
        """
        async with self.uow:
            updated_tenant = await self.uow.tenants.update(tenant)
            await self.uow.commit()
            return updated_tenant
    async def delete_tenant(self, tenant_id: UUID) -> None:
        """Delete a tenant by its ID.
        
        Args:
            tenant_id: Tenant identifier
        """
        async with self.uow:
            await self.uow.tenants.delete(tenant_id)
            await self.uow.commit()
    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Retrieve tenant by its ID.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant entity if found, None otherwise
        """
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(tenant_id)
            return tenant
    async def get_tenants_by_supported_channel(self, channel: str) -> List[Tenant]:
        """Retrieve tenants that support a specific channel.
        
        Args:
            channel: Channel name (e.g., 'email', 'sms')
            
        Returns:
            List of Tenant entities that support the specified channel
        """
        async with self.uow:
            tenants = await self.uow.tenants.get_tenants_by_supported_channel(channel)
            return tenants
    async def get_active_tenants(self) -> List[Tenant]:
        """Retrieve all active tenants.
        
        Returns:
            List of active Tenant entities
        """
        async with self.uow:
            tenants = await self.uow.tenants.find(lambda t: t.is_active)
            return tenants
    
    async def get_tenants_for_rabbitmq(self)->list[Tenant]:
        
        async with self.uow:
            tenants = await self.uow.tenants.find(lambda t: t.prefered_communication_method == "rabbitmq" 
                                                  and t.is_active)
            return tenants
    