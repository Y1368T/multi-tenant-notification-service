from abc import abstractmethod
from typing import Optional
from uuid import UUID

from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
from notification_service.domain.entities.user.user import User


class IUserRepository(IGenericRepository[User]):
    """Repository interface for User entities with custom lookup methods."""

    @abstractmethod
    async def getByKeycloakId(self, keycloakId: str) -> Optional[User]:
        """Find a user by their Keycloak subject ID."""
        pass

    @abstractmethod
    async def getByEmail(self, email: str) -> Optional[User]:
        """Find a user by their email address."""
        pass
