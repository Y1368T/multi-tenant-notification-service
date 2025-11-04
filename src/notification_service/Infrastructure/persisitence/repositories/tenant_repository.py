"""Tenant repository implementation."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository
from notification_service.Infrastructure.persisitence.models.tenant.tenant import TenantModel
from notification_service.domain.entities.tenant import Tenant
from notification_service.Infrastructure.persisitence.mappers.tenant_mapper import TenantMapper

class TenantRepository(GenericRepository[TenantModel, Tenant], ITenantRepository):
    """Repository for tenants with custom methods."""

    def __init__(self, session: AsyncSession, mapper: TenantMapper):
        super().__init__(session, TenantModel, mapper)
        self.session = session
        self.mapper = mapper

    async def get_by_name(self, tenant_name: str) -> Tenant | None:
        """Get tenant by its name."""
        query = select(TenantModel).where(TenantModel.name == tenant_name)
        result = await self.session.execute(query)
        return self.mapper.to_entity(result.scalars().first())
    
    async def get_tenant_by_prefix(self, prefix: str) -> Tenant | None:
        """Get tenant by name prefix."""
        query = select(TenantModel).where(TenantModel.prefix.startswith(prefix))
        result = await self.session.execute(query)
        return self.mapper.to_entity(result.scalars().first())
    
    async def get_tenants_by_channel_support(self, channel: str) -> list[Tenant | None]:
        """Get tenants that support a specific notification channel."""
        query = select(TenantModel).where(TenantModel.supported_channels.contains([channel]))
        result = await self.session.execute(query)
        return self.mapper.to_list_of_entities(result.scalars().all())
    
    async def get_active_tenants(self) -> list[Tenant | None]:
        """Get all active tenants."""
        query = select(TenantModel).where(TenantModel.is_active == True)
        result = await self.session.execute(query)
        return self.mapper.to_list_of_entities(result.scalars().all())
    