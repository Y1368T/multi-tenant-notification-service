"""Mapper for SmsTemplate entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.infrastructure.persisitence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persisitence.mappers.tenant_mapper import TenantMapper
           

class SmsTemplateMapper:
    """Mapper for converting between SmsTemplate entity and SmsTemplateModel."""
    
    @staticmethod
    def to_entity(model: SmsTemplateModel) -> SmsTemplate:
        """Convert database model to domain entity.
        
        Args:
            model: SmsTemplateModel from database

        Returns:
            SmsTemplate domain entity
        """
        if model is None:
            return None
        
        # Map tenant relationship if loaded (avoid lazy loading)
        tenant_entity = None
        insp = inspect(model)
        if 'tenant' in insp.unloaded:
            # Relationship not loaded, skip it
            tenant_entity = None
        elif hasattr(model, 'tenant') and model.__dict__.get('tenant') is not None:
            # Relationship is loaded and not None
            tenant_entity = TenantMapper.to_entity(model.__dict__['tenant'])

        return SmsTemplate(
            id=model.id,
            tenant_id=model.tenant_id,
            template_name=model.template_name,
            content=model.content,
            service_name=model.service_name,
            is_active=model.is_active,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant=tenant_entity
        )
    
    @staticmethod
    def to_model(entity: SmsTemplate) -> SmsTemplateModel:
        """Convert domain entity to database model.
        
        Args:
            entity: SmsTemplate domain entity

        Returns:
            SmsTemplateModel for database
        """
        if entity is None:
            return None

        return SmsTemplateModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            template_name=entity.template_name,
            content=entity.content,
            service_name=entity.service_name,
            is_active=entity.is_active,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[SmsTemplateModel]) -> list[SmsTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SmsTemplateModel from database

        Returns:
            List of SmsTemplate domain entities
        """
        return [SmsTemplateMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[SmsTemplate]) -> list[SmsTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SmsTemplate domain entities

        Returns:
            List of SmsTemplateModel for database
        """
        return [SmsTemplateMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: SmsTemplateModel, entity: SmsTemplate) -> SmsTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SmsTemplateModel
            entity: SmsTemplate with updated data
            
        Returns:
            Updated SmsTemplateModel
        """
        model.tenant_id = entity.tenant_id
        model.template_name = entity.template_name
        model.content = entity.content
        model.service_name = entity.service_name
        model.is_active = entity.is_active
        model.version = entity.version
        model.updated_at = entity.updated_at
        
        return model
