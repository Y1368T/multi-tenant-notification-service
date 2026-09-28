"""User-Tenant repository implementation."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iuser_tenant_repository import IUserTenantRepository
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel
from notification_service.domain.entities.user.user_tenant import UserTenant
from notification_service.infrastructure.persistence.mappers.user_tenant_mapper import UserTenantMapper


class UserTenantRepository(IUserTenantRepository):
    """Repository for UserTenant junction table."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserTenantMapper()

    async def add(self, userTenant: UserTenant) -> UserTenant:
        model = self.mapper.toModel(userTenant)
        self.session.add(model)
        await self.session.flush()
        return self.mapper.toEntity(model)

    async def getByUserAndTenant(
        self, userId: UUID, tenantId: UUID
    ) -> Optional[UserTenant]:
        query = (
            select(UserTenantModel)
            .where(
                UserTenantModel.user_id == userId,
                UserTenantModel.tenant_id == tenantId,
            )
            .options(
                selectinload(UserTenantModel.tenant),
                selectinload(UserTenantModel.user),
            )
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        return self.mapper.toEntity(model)

    async def getByUserId(self, userId: UUID) -> List[UserTenant]:
        query = (
            select(UserTenantModel)
            .where(UserTenantModel.user_id == userId)
            .options(selectinload(UserTenantModel.tenant))
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return self.mapper.toListOfEntities(models)

    async def getByTenantId(self, tenantId: UUID) -> List[UserTenant]:
        query = (
            select(UserTenantModel)
            .where(UserTenantModel.tenant_id == tenantId)
            .options(selectinload(UserTenantModel.user))
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return self.mapper.toListOfEntities(models)

    async def update(self, userTenant: UserTenant) -> UserTenant:
        existing = await self.getByUserAndTenant(userTenant.userId, userTenant.tenantId)
        if existing is None:
            raise ValueError(f"UserTenant not found for userId={userTenant.userId}")
        query = select(UserTenantModel).where(
            UserTenantModel.user_id == userTenant.userId,
            UserTenantModel.tenant_id == userTenant.tenantId,
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        model.role = userTenant.role
        model.isActive = userTenant.isActive
        await self.session.flush()
        return self.mapper.toEntity(model)

    async def delete(self, userId: UUID, tenantId: UUID) -> None:
        query = delete(UserTenantModel).where(
            UserTenantModel.user_id == userId,
            UserTenantModel.tenant_id == tenantId,
        )
        await self.session.execute(query)
        await self.session.flush()
