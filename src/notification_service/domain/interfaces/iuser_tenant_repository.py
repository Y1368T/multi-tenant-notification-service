from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from notification_service.domain.entities.user.user_tenant import UserTenant


class IUserTenantRepository(ABC):
    """Repository interface for UserTenant entities.
    
    Note: UserTenant uses a composite PK so it does NOT extend
    IGenericRepository which assumes a single UUID 'id' field.
    """

    @abstractmethod
    async def add(self, userTenant: UserTenant) -> UserTenant:
        """Create a new user-tenant membership."""
        pass

    @abstractmethod
    async def getByUserAndTenant(
        self, userId: UUID, tenantId: UUID
    ) -> Optional[UserTenant]:
        """Find a specific user-tenant membership."""
        pass

    @abstractmethod
    async def getByUserId(self, userId: UUID) -> List[UserTenant]:
        """Get all tenant memberships for a user."""
        pass

    @abstractmethod
    async def getByTenantId(self, tenantId: UUID) -> List[UserTenant]:
        """Get all user memberships within a tenant."""
        pass

    @abstractmethod
    async def update(self, userTenant: UserTenant) -> UserTenant:
        """Update a user-tenant membership (e.g., change role)."""
        pass

    @abstractmethod
    async def delete(self, userId: UUID, tenantId: UUID) -> None:
        """Remove a user from a tenant."""
        pass
