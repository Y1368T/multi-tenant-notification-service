from typing import Generic, TypeVar
from notification_service.domain.interfaces.igeneric_repository import IGenericRepository

T = TypeVar('T')
class ITenantRepository(IGenericRepository[T], Generic[T]):
    """Interface for tenant-specific repository operations."""
    async def getByName(self, tenantName: str) -> T | None:
        """Get tenant by its name."""
        pass
    
    async def getTenantByPrefix(self, prefix: str) -> T | None:
        """Get tenants by name prefix."""
        pass
    
    async def getTenantsBySupportedChannel(self, channel: str) -> list[T]:
        """Get tenants that support a specific notification channel."""
        pass
    
    async def get_by_api_key(self, api_key: str) -> T | None:
        """Get tenant by API key."""
        pass
    
    async def get_by_api_key_and_prefix(self, api_key: str, prefix: str) -> T | None:
        """Get tenant by API key and prefix (for RabbitMQ queue validation)."""
        pass