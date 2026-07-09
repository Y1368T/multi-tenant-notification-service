"""Mapper for TenantWhatsAppConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.infrastructure.persistence.models.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfigurationModel


class TenantWhatsAppConfigurationMapper:
    """Mapper for converting between TenantWhatsAppConfiguration entity and TenantWhatsAppConfigurationModel."""
    
    @staticmethod
    def toEntity(model: TenantWhatsAppConfigurationModel) -> TenantWhatsAppConfiguration:
        """Convert database model to domain entity.
        
        Args:
            model: TenantWhatsAppConfigurationModel from database
            
        Returns:
            TenantWhatsAppConfiguration domain entity
        """
        if model is None:
            return None
        
        return TenantWhatsAppConfiguration(
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
    def toModel(entity: TenantWhatsAppConfiguration) -> TenantWhatsAppConfigurationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: TenantWhatsAppConfiguration domain entity
            
        Returns:
            TenantWhatsAppConfigurationModel for database
        """
        if entity is None:
            return None
        
        return TenantWhatsAppConfigurationModel(
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
    def toListOfEntities(models: list[TenantWhatsAppConfigurationModel]) -> list[TenantWhatsAppConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantWhatsAppConfigurationModel from database
            
        Returns:
            List of TenantWhatsAppConfiguration domain entities
        """
        return [TenantWhatsAppConfigurationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TenantWhatsAppConfiguration]) -> list[TenantWhatsAppConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantWhatsAppConfiguration domain entities
            
        Returns:
            List of TenantWhatsAppConfigurationModel for database
        """
        return [TenantWhatsAppConfigurationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TenantWhatsAppConfigurationModel, entity: TenantWhatsAppConfiguration) -> TenantWhatsAppConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantWhatsAppConfigurationModel
            entity: TenantWhatsAppConfiguration with updated data
            
        Returns:
            Updated TenantWhatsAppConfigurationModel
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
