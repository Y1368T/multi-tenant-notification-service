"""Mapper for TenantEmailConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.Infrastructure.persisitence.models.tenant.tenant_email_configuration import TenantEmailConfigurationModel


class TenantEmailConfigurationMapper:
    """Mapper for converting between TenantEmailConfiguration entity and TenantEmailConfigurationModel."""
    
    @staticmethod
    def to_entity(model: TenantEmailConfigurationModel) -> TenantEmailConfiguration:
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
            tenant_id=model.tenant_id,
            provider_name=model.provider_name,
            config=model.config,
            priority=model.priority,
            is_active=model.is_active,
            rate_limit_per_minute=model.rate_limit_per_minute,
            rate_limit_per_hour=model.rate_limit_per_hour,
            rate_limit_per_day=model.rate_limit_per_day,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: TenantEmailConfiguration) -> TenantEmailConfigurationModel:
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
            tenant_id=entity.tenant_id,
            provider_name=entity.provider_name,
            config=entity.config,
            priority=entity.priority,
            is_active=entity.is_active,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            rate_limit_per_hour=entity.rate_limit_per_hour,
            rate_limit_per_day=entity.rate_limit_per_day,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[TenantEmailConfigurationModel]) -> list[TenantEmailConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantEmailConfigurationModel from database
            
        Returns:
            List of TenantEmailConfiguration domain entities
        """
        return [TenantEmailConfigurationMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[TenantEmailConfiguration]) -> list[TenantEmailConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantEmailConfiguration domain entities
            
        Returns:
            List of TenantEmailConfigurationModel for database
        """
        return [TenantEmailConfigurationMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: TenantEmailConfigurationModel, entity: TenantEmailConfiguration) -> TenantEmailConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantEmailConfigurationModel
            entity: TenantEmailConfiguration with updated data
            
        Returns:
            Updated TenantEmailConfigurationModel
        """
        model.tenant_id = entity.tenant_id
        model.provider_name = entity.provider_name
        model.config = entity.config
        model.priority = entity.priority
        model.is_active = entity.is_active
        model.rate_limit_per_minute = entity.rate_limit_per_minute
        model.rate_limit_per_hour = entity.rate_limit_per_hour
        model.rate_limit_per_day = entity.rate_limit_per_day
        model.updated_at = entity.updated_at
        
        return model
