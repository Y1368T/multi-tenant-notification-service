"""Mapper for TenantInAppConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.infrastructure.persistence.models.tenant.tenant_inapp_configuration import TenantInAppConfigurationModel


class TenantInAppConfigurationMapper:
    """Mapper for converting between TenantInAppConfiguration entity and TenantInAppConfigurationModel."""
    
    @staticmethod
    def toEntity(model: TenantInAppConfigurationModel) -> TenantInAppConfiguration:
        """Convert database model to domain entity.
        
        Args:
            model: TenantInAppConfigurationModel from database
            
        Returns:
            TenantInAppConfiguration domain entity
        """
        if model is None:
            return None
        
        return TenantInAppConfiguration(
            id=model.id,
            tenantId=model.tenantId,
            providerName=model.providerName,
            priority=model.priority,
            config=model.config,
            isActive=model.isActive,
            rateLimitPerMinute=model.rateLimitPerMinute,
            rateLimitPerHour=model.rateLimitPerHour,
            rateLimitPerDay=model.rateLimitPerDay,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TenantInAppConfiguration) -> TenantInAppConfigurationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: TenantInAppConfiguration domain entity
            
        Returns:
            TenantInAppConfigurationModel for database
        """
        if entity is None:
            return None
        
        return TenantInAppConfigurationModel(
            id=entity.id,
            tenantId=entity.tenantId,
            providerName=entity.providerName,
            priority=entity.priority,
            config=entity.config,
            isActive=entity.isActive,
            rateLimitPerMinute=entity.rateLimitPerMinute,
            rateLimitPerHour=entity.rateLimitPerHour,
            rateLimitPerDay=entity.rateLimitPerDay,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TenantInAppConfigurationModel]) -> list[TenantInAppConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantInAppConfigurationModel from database
            
        Returns:
            List of TenantInAppConfiguration domain entities
        """
        return [TenantInAppConfigurationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TenantInAppConfiguration]) -> list[TenantInAppConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantInAppConfiguration domain entities
            
        Returns:
            List of TenantInAppConfigurationModel for database
        """
        return [TenantInAppConfigurationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantInAppConfigurationModel, entity: TenantInAppConfiguration) -> TenantInAppConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantInAppConfigurationModel
            entity: TenantInAppConfiguration with updated data
            
        Returns:
            Updated TenantInAppConfigurationModel
        """
        model.tenantId = entity.tenantId
        model.providerName = entity.providerName
        model.priority = entity.priority
        model.config = entity.config
        model.isActive = entity.isActive
        model.rateLimitPerMinute = entity.rateLimitPerMinute
        model.rateLimitPerHour = entity.rateLimitPerHour
        model.rateLimitPerDay = entity.rateLimitPerDay
        model.updatedAt = entity.updatedAt
        
        return model
