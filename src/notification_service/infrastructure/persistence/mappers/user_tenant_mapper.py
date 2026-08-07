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

        # Avoid triggering async lazy loads while the session is still in-flight.
        if "tenant" in model.__dict__ and model.__dict__["tenant"] is not None:
            entity.tenantName = model.__dict__["tenant"].name or ""
            entity.tenantPrefix = model.__dict__["tenant"].prefix or ""
        if "user" in model.__dict__ and model.__dict__["user"] is not None:
            entity.userEmail = model.__dict__["user"].email or ""
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
