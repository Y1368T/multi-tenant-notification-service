"""Tenant repository implementation."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository
from notification_service.infrastructure.persisitence.models.tenant.tenant import TenantModel
from notification_service.domain.entities.tenant import Tenant
from notification_service.infrastructure.persisitence.mappers.tenant_mapper import TenantMapper

class TenantRepository(GenericRepository[TenantModel, Tenant], ITenantRepository):
    """Repository for tenants with custom methods."""

    def __init__(self, session: AsyncSession, mapper: TenantMapper):
        super().__init__(session, TenantModel, mapper)
        self.session = session
        self.mapper = mapper

    async def getByName(self, tenantName: str) -> Tenant | None:
        """Get tenant by its name."""
        query = select(TenantModel).where(TenantModel.name == tenantName)
        result = await self.session.execute(query)
        return self.mapper.toEntity(result.scalars().first())
    
    async def getTenantByPrefix(self, prefix: str) -> Tenant | None:
        """Get tenant by name prefix."""
        query = select(TenantModel).where(TenantModel.prefix == prefix)
        result = await self.session.execute(query)
        return self.mapper.toEntity(result.scalars().first())
    
    async def getTenantsBySupportedChannel(self, channel: str) -> list[Tenant | None]:
        """Get tenants that support a specific notification channel."""
        query = select(TenantModel).where(TenantModel.supportedChannels.contains([channel]))
        result = await self.session.execute(query)
        return self.mapper.toListOfEntities(result.scalars().all())
    
    async def getActiveTenants(self) -> list[Tenant | None]:
        """Get all active tenants."""
        query = select(TenantModel).where(TenantModel.isActive == True)
        result = await self.session.execute(query)
        return self.mapper.toListOfEntities(result.scalars().all())
    