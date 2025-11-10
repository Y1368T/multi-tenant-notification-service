"""Mapper for TenantSMSConfiguration entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.infrastructure.persisitence.models.tenant.tenant_sms_configuration import TenantSMSConfigurationModel


class TenantSmsConfigurationMapper:
    """Mapper for converting between TenantSMSConfiguration entity and TenantSMSConfigurationModel."""
    
    @staticmethod
    def to_entity(model: TenantSMSConfigurationModel) -> TenantSMSConfiguration:
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
            tenant_id=model.tenant_id,
            provider_name=model.provider_name,
            config=model.config,
            is_active=model.is_active,
            rate_limit_per_minute=model.rate_limit_per_minute,
            rate_limit_per_hour=model.rate_limit_per_hour,
            rate_limit_per_day=model.rate_limit_per_day,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: TenantSMSConfiguration) -> TenantSMSConfigurationModel:
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
            tenant_id=entity.tenant_id,
            provider_name=entity.provider_name,
            config=entity.config,
            is_active=entity.is_active,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            rate_limit_per_hour=entity.rate_limit_per_hour,
            rate_limit_per_day=entity.rate_limit_per_day,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[TenantSMSConfigurationModel]) -> list[TenantSMSConfiguration]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantSMSConfigurationModel from database
            
        Returns:
            List of TenantSMSConfiguration domain entities
        """
        return [TenantSmsConfigurationMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[TenantSMSConfiguration]) -> list[TenantSMSConfigurationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of TenantSMSConfiguration domain entities
            
        Returns:
            List of TenantSMSConfigurationModel for database
        """
        return [TenantSmsConfigurationMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: TenantSMSConfigurationModel, entity: TenantSMSConfiguration) -> TenantSMSConfigurationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantSMSConfigurationModel
            entity: TenantSMSConfiguration with updated data
            
        Returns:
            Updated TenantSMSConfigurationModel
        """
        model.tenant_id = entity.tenant_id
        model.provider_name = entity.provider_name
        model.config = entity.config
        model.is_active = entity.is_active
        model.rate_limit_per_minute = entity.rate_limit_per_minute
        model.rate_limit_per_hour = entity.rate_limit_per_hour
        model.rate_limit_per_day = entity.rate_limit_per_day
        model.updated_at = entity.updated_at
        
        return model
