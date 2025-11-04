from typing import List,Optional
from uuid import UUID
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.domain.interfaces import IUnitOfWork


class TenantService:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
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
            created_tenant = await self.uow.tenants.add(tenant)
            await self.uow.commit()
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
    