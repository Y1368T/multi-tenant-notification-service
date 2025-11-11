"""Mapper for TenantEmailConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.infrastructure.persisitence.models.tenant.tenant_email_configuration import TenantEmailConfigurationModel


class TenantEmailConfigurationMapper:
    """Mapper for converting between TenantEmailConfiguration entity and TenantEmailConfigurationModel."""
    
    @staticmethod
    def toEntity(model: TenantEmailConfigurationModel) -> TenantEmailConfiguration:
        """Convert database model to domain entity.
        
        Args:
            model: TenantEmailConfigurationModel from database
            
        Returns:
            TenantEmailConfiguration domain entity
        """
        if model is None:
            return None
        
        return TenantEmailConfiguration(
            id=model.id,
            tenantId=model.tenantId,
            providerName=model.providerName,
            config=model.config,
            priority=model.priority,
            isActive=model.isActive,
            rateLimitPerMinute=model.rateLimitPerMinute,
            rateLimitPerHour=model.rateLimitPerHour,
            rateLimitPerDay=model.rateLimitPerDay,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TenantEmailConfiguration) -> TenantEmailConfigurationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: TenantEmailConfiguration domain entity
            
        Returns:
            TenantEmailConfigurationModel for database
        """
        if entity is None:
            return None
        
        return TenantEmailConfigurationModel(
            id=entity.id,
            tenantId=entity.tenantId,
            providerName=entity.providerName,
            config=entity.config,
            priority=entity.priority,
            isActive=entity.isActive,
            rateLimitPerMinute=entity.rateLimitPerMinute,
            rateLimitPerHour=entity.rateLimitPerHour,
            rateLimitPerDay=entity.rateLimitPerDay,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TenantEmailConfigurationModel]) -> list[TenantEmailConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantEmailConfigurationModel from database
            
        Returns:
            List of TenantEmailConfiguration domain entities
        """
        return [TenantEmailConfigurationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TenantEmailConfiguration]) -> list[TenantEmailConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantEmailConfiguration domain entities
            
        Returns:
            List of TenantEmailConfigurationModel for database
        """
        return [TenantEmailConfigurationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantEmailConfigurationModel, entity: TenantEmailConfiguration) -> TenantEmailConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantEmailConfigurationModel
            entity: TenantEmailConfiguration with updated data
            
        Returns:
            Updated TenantEmailConfigurationModel
        """
        model.tenantId = entity.tenantId
        model.providerName = entity.providerName
        model.config = entity.config
        model.priority = entity.priority
        model.isActive = entity.isActive
        model.rateLimitPerMinute = entity.rateLimitPerMinute
        model.rateLimitPerHour = entity.rateLimitPerHour
        model.rateLimitPerDay = entity.rateLimitPerDay
        model.updatedAt = entity.updatedAt
        
        return model
