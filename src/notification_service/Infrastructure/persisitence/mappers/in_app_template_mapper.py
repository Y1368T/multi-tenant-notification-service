"""Mapper for InAppTemplate entity and model."""
from typing import Optional
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from notification_service.infrastructure.persisitence.models.in_app.in_app_template import InAppTemplateModel


class InAppTemplateMapper:
    """Mapper for converting between InAppTemplate entity and InAppTemplateModel."""
    
    @staticmethod
    def to_entity(model: InAppTemplateModel) -> InAppTemplate:
        """Convert database model to domain entity.
        
        Args:
            model: InAppTemplateModel from database
            
        Returns:
            InAppTemplate domain entity
        """
        if model is None:
            return None
        
        return InAppTemplate(
            id=model.id,
            template_name=model.template_name,
            body=model.body,
            service_name=model.service_name,
            tenant_id=model.tenant_id,
            is_active=model.is_active,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: InAppTemplate) -> InAppTemplateModel:
        """Convert domain entity to database model.
        
        Args:
            entity: InAppTemplate domain entity
            
        Returns:
            InAppTemplateModel for database
        """
        if entity is None:
            return None
        
        return InAppTemplateModel(
            id=entity.id,
            template_name=entity.template_name,
            body=entity.body,
            service_name=entity.service_name,
            tenant_id=entity.tenant_id,
            is_active=entity.is_active,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[InAppTemplateModel]) -> list[InAppTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of InAppTemplateModel from database
            
        Returns:
            List of InAppTemplate domain entities
        """
        return [InAppTemplateMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[InAppTemplate]) -> list[InAppTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of InAppTemplate domain entities
            
        Returns:
            List of InAppTemplateModel for database
        """
        return [InAppTemplateMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: InAppTemplateModel, entity: InAppTemplate) -> InAppTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing InAppTemplateModel
            entity: InAppTemplate with updated data
            
        Returns:
            Updated InAppTemplateModel
        """
        model.template_name = entity.template_name
        model.body = entity.body
        model.service_name = entity.service_name
        model.tenant_id = entity.tenant_id
        model.is_active = entity.is_active
        model.version = entity.version
        model.updated_at = entity.updated_at
        
        return model
