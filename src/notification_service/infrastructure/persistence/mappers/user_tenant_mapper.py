"""Mapper for UserTenant entity and UserTenantModel."""
from typing import Optional
from notification_service.domain.entities.user.user_tenant import UserTenant
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel


class UserTenantMapper:
    """Converts between UserTenant domain entity and UserTenantModel (DB)."""

    @staticmethod
    def toEntity(model: Optional[UserTenantModel]) -> Optional[UserTenant]:
        if model is None:
            return None
        entity = UserTenant(
            userId=model.user_id,
            tenantId=model.tenant_id,
            role=model.role,
            isActive=model.isActive,
            joinedAt=model.joinedAt,
        )

        if getattr(model, "tenant", None):
            entity.tenantName = model.tenant.name or ""
            entity.tenantPrefix = model.tenant.prefix or ""
        if getattr(model, "user", None):
            entity.userEmail = model.user.email or ""
        return entity

    @staticmethod
    def toModel(entity: UserTenant) -> UserTenantModel:
        if entity is None:
            return None
        return UserTenantModel(
            user_id=entity.userId,
            tenant_id=entity.tenantId,
            role=entity.role,
            isActive=entity.isActive,
            joinedAt=entity.joinedAt,
        )

    @staticmethod
    def toListOfEntities(models: list) -> list:
        return [UserTenantMapper.toEntity(m) for m in models]
