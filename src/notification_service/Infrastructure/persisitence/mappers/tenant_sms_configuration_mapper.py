"""Mapper for TenantSMSConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.infrastructure.persisitence.models.tenant.tenant_sms_configuration import TenantSMSConfigurationModel


class TenantSmsConfigurationMapper:
    """Mapper for converting between TenantSMSConfiguration entity and TenantSMSConfigurationModel."""
    
    @staticmethod
    def toEntity(model: TenantSMSConfigurationModel) -> TenantSMSConfiguration:
        """Convert database model to domain entity.
        
        Args:
            model: TenantSMSConfigurationModel from database
            
        Returns:
            TenantSMSConfiguration domain entity
        """
        if model is None:
            return None
        
        return TenantSMSConfiguration(
            id=model.id,
            tenantId=model.tenantId,
            providerName=model.providerName,
            config=model.config,
            isActive=model.isActive,
            rateLimitPerMinute=model.rateLimitPerMinute,
            rateLimitPerHour=model.rateLimitPerHour,
            rateLimitPerDay=model.rateLimitPerDay,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TenantSMSConfiguration) -> TenantSMSConfigurationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: TenantSMSConfiguration domain entity
            
        Returns:
            TenantSMSConfigurationModel for database
        """
        if entity is None:
            return None
        
        return TenantSMSConfigurationModel(
            id=entity.id,
            tenantId=entity.tenantId,
            providerName=entity.providerName,
            config=entity.config,
            isActive=entity.isActive,
            rateLimitPerMinute=entity.rateLimitPerMinute,
            rateLimitPerHour=entity.rateLimitPerHour,
            rateLimitPerDay=entity.rateLimitPerDay,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TenantSMSConfigurationModel]) -> list[TenantSMSConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantSMSConfigurationModel from database
            
        Returns:
            List of TenantSMSConfiguration domain entities
        """
        return [TenantSmsConfigurationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TenantSMSConfiguration]) -> list[TenantSMSConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantSMSConfiguration domain entities
            
        Returns:
            List of TenantSMSConfigurationModel for database
        """
        return [TenantSmsConfigurationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantSMSConfigurationModel, entity: TenantSMSConfiguration) -> TenantSMSConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantSMSConfigurationModel
            entity: TenantSMSConfiguration with updated data
            
        Returns:
            Updated TenantSMSConfigurationModel
        """
        model.tenantId = entity.tenantId
        model.providerName = entity.providerName
        model.config = entity.config
        model.isActive = entity.isActive
        model.rateLimitPerMinute = entity.rateLimitPerMinute
        model.rateLimitPerHour = entity.rateLimitPerHour
        model.rateLimitPerDay = entity.rateLimitPerDay
        model.updatedAt = entity.updatedAt
        
        return model
