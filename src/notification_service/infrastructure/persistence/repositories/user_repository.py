"""User repository implementation."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.domain.interfaces.iuser_repository import IUserRepository
from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.domain.entities.user.user import User
from notification_service.infrastructure.persistence.mappers.user_mapper import UserMapper


class UserRepository(GenericRepository[UserModel, User], IUserRepository):
    """Repository for User entities with custom lookup methods."""

    def __init__(self, session: AsyncSession, mapper: UserMapper):
        super().__init__(session, UserModel, mapper)

    async def getByKeycloakId(self, keycloakId: str) -> Optional[User]:
        """Find a user by their Keycloak subject ID (the 'sub' JWT claim)."""
        query = select(UserModel).where(UserModel.keycloakId == keycloakId)
        result = await self.session.execute(query)
        model = result.scalars().first()
        return self.mapper.toEntity(model)

    async def getByEmail(self, email: str) -> Optional[User]:
        """Find a user by their email address."""
        query = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(query)
        model = result.scalars().first()
        return self.mapper.toEntity(model)
