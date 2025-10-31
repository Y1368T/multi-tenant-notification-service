"""Mapper for EmailTemplate entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.Infrastructure.persisitence.models.email.email_template import EmailTemplateModel


class EmailTemplateMapper:
    """Mapper for converting between EmailTemplate entity and EmailTemplateModel."""
    
    @staticmethod
    def to_entity(model: EmailTemplateModel) -> EmailTemplate:
        """Convert database model to domain entity.
        
        Args:
            model: EmailTemplateModel from database
            
        Returns:
            EmailTemplate domain entity
        """
        if model is None:
            return None
        
        return EmailTemplate(
            id=model.id,
            template_name=model.template_name,
            subject=model.subject,
            body=model.body,
            service_name=model.service_name,
            tenant_id=model.tenant_id,
            body_type=model.body_type,
            file_urls=model.file_urls,
            is_active=model.is_active,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: EmailTemplate) -> EmailTemplateModel:
        """Convert domain entity to database model.
        
        Args:
            entity: EmailTemplate domain entity
            
        Returns:
            EmailTemplateModel for database
        """
        if entity is None:
            return None
        
        return EmailTemplateModel(
            id=entity.id,
            template_name=entity.template_name,
            subject=entity.subject,
            body=entity.body,
            service_name=entity.service_name,
            tenant_id=entity.tenant_id,
            body_type=entity.body_type,
            file_urls=entity.file_urls,
            is_active=entity.is_active,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[EmailTemplateModel]) -> list[EmailTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailTemplateModel from database
            
        Returns:
            List of EmailTemplate domain entities
        """
        return [EmailTemplateMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[EmailTemplate]) -> list[EmailTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of EmailTemplate domain entities
            
        Returns:
            List of EmailTemplateModel for database
        """
        return [EmailTemplateMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: EmailTemplateModel, entity: EmailTemplate) -> EmailTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailTemplateModel
            entity: EmailTemplate with updated data
            
        Returns:
            Updated EmailTemplateModel
        """
        model.template_name = entity.template_name
        model.subject = entity.subject
        model.body = entity.body
        model.service_name = entity.service_name
        model.tenant_id = entity.tenant_id
        model.body_type = entity.body_type
        model.file_urls = entity.file_urls
        model.is_active = entity.is_active
        model.version = entity.version
        model.updated_at = entity.updated_at
        
        return model
