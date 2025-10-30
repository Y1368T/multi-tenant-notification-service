from select import select
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository
from notification_service.Infrastructure.persisitence.models import TenantModel as Tenant
class TenantRepository(ITenantRepository):
    """Concrete implementation of ITenantRepository for tenant-specific operations."""
    
    async def get_by_name(self, tenant_name: str) -> Tenant | None:
        """Get tenant by its name."""
        query = select(Tenant).where(Tenant.name == tenant_name)
        result = await self._session.execute(query)
        return result.scalars().first()
    
    async def get_tenant_by_prefix(self, prefix: str) -> Tenant | None:
        """Get tenants by name prefix."""
        query = select(Tenant).where(Tenant.prefix.startswith(prefix))
        result = await self._session.execute(query)
        return result.scalars().first()
    
    async def get_tenants_by_channel_support(self, channel: str) -> list[Tenant]:
        """Get tenants that support a specific notification channel."""
        query = select(Tenant).where(Tenant.supported_channels.contains([channel]))
        result = await self._session.execute(query)
        return result.scalars().all()