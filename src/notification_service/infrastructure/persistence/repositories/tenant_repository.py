"""Tenant repository implementation."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.domain.entities.tenant import Tenant
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper

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
    
    async def get_by_api_key(self, api_key: str) -> Tenant | None:
        """Get tenant by API key.
        
        Supports comma-separated API keys in the apiKeys field.
        Matches if the provided api_key is found in the tenant's apiKeys string.
        """
        from sqlalchemy import or_, func
        # Query where apiKeys contains the provided key
        # Handle both exact match and comma-separated values
        query = select(TenantModel).where(
            or_(
                TenantModel.apiKeys == api_key,  # Exact match
                TenantModel.apiKeys.like(f"{api_key},%"),  # Key at start
                TenantModel.apiKeys.like(f"%,{api_key}"),  # Key in middle
                TenantModel.apiKeys.like(f"%,{api_key},%"),  # Key in middle with commas
            )
        )
        result = await self.session.execute(query)
        tenant_model = result.scalars().first()
        return self.mapper.toEntity(tenant_model) if tenant_model else None
    
    async def get_by_api_key_and_prefix(self, api_key: str, prefix: str) -> Tenant | None:
        """Get tenant by API key and prefix (for RabbitMQ queue validation).
        
        This ensures the API key belongs to the tenant that owns the queue.
        """
        from sqlalchemy import or_
        query = select(TenantModel).where(
            TenantModel.prefix == prefix
        ).where(
            or_(
                TenantModel.apiKeys == api_key,
                TenantModel.apiKeys.like(f"{api_key},%"),
                TenantModel.apiKeys.like(f"%,{api_key}"),
                TenantModel.apiKeys.like(f"%,{api_key},%"),
            )
        )
        result = await self.session.execute(query)
        tenant_model = result.scalars().first()
        return self.mapper.toEntity(tenant_model) if tenant_model else None
    