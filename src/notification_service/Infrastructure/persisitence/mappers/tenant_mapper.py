"""Mapper for Tenant entity and model."""
from typing import Optional
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.Infrastructure.persisitence.models.tenant.tenant import TenantModel


class TenantMapper:
    """Mapper for converting between Tenant entity and TenantModel."""
    
    @staticmethod
    def to_entity(model: TenantModel) -> Tenant:
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
            is_active=model.is_active,
            rate_limit_per_minute=model.rate_limit_per_minute,
            rate_limit_per_hour=model.rate_limit_per_hour,
            rate_limit_per_day=model.rate_limit_per_day,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: Tenant) -> TenantModel:
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
            is_active=entity.is_active,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            rate_limit_per_hour=entity.rate_limit_per_hour,
            rate_limit_per_day=entity.rate_limit_per_day,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[TenantModel]) -> list[Tenant]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of TenantModel from database
            
        Returns:
            List of Tenant domain entities
        """
        return [TenantMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[Tenant]) -> list[TenantModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of Tenant domain entities
            
        Returns:
            List of TenantModel for database
        """
        return [TenantMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: TenantModel, entity: Tenant) -> TenantModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing TenantModel
            entity: Tenant with updated data
            
        Returns:
            Updated TenantModel
        """
        model.name = entity.name
        model.prefix = entity.prefix
        model.is_active = entity.is_active
        model.rate_limit_per_minute = entity.rate_limit_per_minute
        model.rate_limit_per_hour = entity.rate_limit_per_hour
        model.rate_limit_per_day = entity.rate_limit_per_day
        model.updated_at = entity.updated_at
        
        return model
