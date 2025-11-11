from typing import TypeVar, Generic
from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
from notification_service.infrastructure.persisitence.models import TenantModel as Tenant

T = TypeVar('T')

class ITenantRepository(IGenericRepository[T], Generic[T]):
    """Interface for tenant-specific repository operations."""
    async def getByName(self, tenantName: str) -> T | None:
        """Get tenant by its name."""
        pass
    async def getTenantByPrefix(self, prefix: str) -> Tenant | None:
        """Get tenants by name prefix."""
        pass
    async def getTenantsBySupportedChannel(self, channel: str) -> list[Tenant]:
        """Get tenants that support a specific notification channel."""
        pass