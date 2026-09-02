from typing import Optional
from notification_service.domain.entities.tenant.tenant_telegram_configuration import TenantTelegramConfiguration
from notification_service.infrastructure.persistence.models.tenant.tenant_telegram_configuration import TenantTelegramConfigurationModel


class TenantTelegramConfigurationMapper:
    """Mapper for converting between TenantTelegramConfiguration entity and TenantTelegramConfigurationModel."""
    
    @staticmethod
    def toEntity(model: TenantTelegramConfigurationModel) -> TenantTelegramConfiguration:
        if model is None:
            return None
        
        return TenantTelegramConfiguration(
            id=model.id,
            tenantId=model.tenantId,
            providerName=model.providerName,
            priority=model.priority,
            isActive=model.isActive,
            rateLimitPerMinute=model.rateLimitPerMinute,
            rateLimitPerHour=model.rateLimitPerHour,
            rateLimitPerDay=model.rateLimitPerDay,
            config=model.config,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TenantTelegramConfiguration) -> TenantTelegramConfigurationModel:
        if entity is None:
            return None
        
        return TenantTelegramConfigurationModel(
            id=entity.id,
            tenantId=entity.tenantId,
            providerName=entity.providerName,
            priority=entity.priority,
            isActive=entity.isActive,
            rateLimitPerMinute=entity.rateLimitPerMinute,
            rateLimitPerHour=entity.rateLimitPerHour,
            rateLimitPerDay=entity.rateLimitPerDay,
            config=entity.config,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TenantTelegramConfigurationModel]) -> list[TenantTelegramConfiguration]:
        return [TenantTelegramConfigurationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TenantTelegramConfiguration]) -> list[TenantTelegramConfigurationModel]:
        return [TenantTelegramConfigurationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantTelegramConfigurationModel, entity: TenantTelegramConfiguration) -> TenantTelegramConfigurationModel:
        model.tenantId = entity.tenantId
        model.providerName = entity.providerName
        model.priority = entity.priority
        model.isActive = entity.isActive
        model.rateLimitPerMinute = entity.rateLimitPerMinute
        model.rateLimitPerHour = entity.rateLimitPerHour
        model.rateLimitPerDay = entity.rateLimitPerDay
        model.config = entity.config
        model.updatedAt = entity.updatedAt
        
        return model
