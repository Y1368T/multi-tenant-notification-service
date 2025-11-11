"""Mapper for Tenant entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.infrastructure.persisitence.models.tenant.tenant import TenantModel


class TenantMapper:
    """Mapper for converting between Tenant entity and TenantModel."""
    
    @staticmethod
    def toEntity(model: TenantModel) -> Tenant:
        """Convert database model to domain entity.
        
        Args:
            model: TenantModel from database
            
        Returns:
            Tenant domain entity
        """
        if model is None:
            return None
        
        return Tenant(
            id=model.id,
            name=model.name,
            prefix=model.prefix,
            isActive=model.isActive,
            apiKeys=model.apiKeys,
            preferedCommunicationMethod=model.preferedCommunicationMethod,
            supportedChannels=model.supportedChannels,
            rateLimitPerMinute=model.rateLimitPerMinute,
            rateLimitPerHour=model.rateLimitPerHour,
            rateLimitPerDay=model.rateLimitPerDay,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: Tenant) -> TenantModel:
        """Convert domain entity to database model.
        
        Args:
            entity: Tenant domain entity
            
        Returns:
            TenantModel for database
        """
        if entity is None:
            return None
        
        return TenantModel(
            id=entity.id,
            name=entity.name,
            prefix=entity.prefix,
            isActive=entity.isActive,
            apiKeys=entity.apiKeys,
            preferedCommunicationMethod=entity.preferedCommunicationMethod,
            supportedChannels=entity.supportedChannels,
            rateLimitPerMinute=entity.rateLimitPerMinute,
            rateLimitPerHour=entity.rateLimitPerHour,
            rateLimitPerDay=entity.rateLimitPerDay,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TenantModel]) -> list[Tenant]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantModel from database
            
        Returns:
            List of Tenant domain entities
        """
        return [TenantMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[Tenant]) -> list[TenantModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of Tenant domain entities
            
        Returns:
            List of TenantModel for database
        """
        return [TenantMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantModel, entity: Tenant) -> TenantModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantModel
            entity: Tenant with updated data
            
        Returns:
            Updated TenantModel
        """
        model.name = entity.name
        model.prefix = entity.prefix
        model.isActive = entity.isActive
        model.supportedChannels=entity.supportedChannels
        model.apiKeys=entity.apiKeys
        model.preferedCommunicationMethod=entity.preferedCommunicationMethod
        model.rateLimitPerMinute = entity.rateLimitPerMinute
        model.rateLimitPerHour = entity.rateLimitPerHour
        model.rateLimitPerDay = entity.rateLimitPerDay
        model.updatedAt = entity.updatedAt
        
        return model
