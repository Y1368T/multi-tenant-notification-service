"""Mapper for User entity and UserModel."""
from typing import Optional
from notification_service.domain.entities.user.user import User
from notification_service.infrastructure.persistence.models.user.user import UserModel


class UserMapper:
    """Converts between User domain entity and UserModel (DB)."""

    @staticmethod
    def toEntity(model: Optional[UserModel]) -> Optional[User]:
        if model is None:
            return None
        return User(
            id=model.id,
            keycloakId=model.keycloakId,
            email=model.email,
            fullName=model.fullName,
            role=model.role,
            isActive=model.isActive,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt,
        )

    @staticmethod
    def toModel(entity: User) -> UserModel:
        if entity is None:
            return None
        return UserModel(
            id=entity.id,
            keycloakId=entity.keycloakId,
            email=entity.email,
            fullName=entity.fullName,
            role=entity.role,
            isActive=entity.isActive,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt,
        )

    @staticmethod
    def toListOfEntities(models: list) -> list:
        return [UserMapper.toEntity(m) for m in models]

    @staticmethod
    def updateModelFromEntity(model: UserModel, entity: User) -> UserModel:
        model.email = entity.email
        model.fullName = entity.fullName
        model.role = entity.role
        model.isActive = entity.isActive
        model.updatedAt = entity.updatedAt
        return model
