"""Mapper for WhatsAppTemplate entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper
           

class WhatsAppTemplateMapper:
    """Mapper for converting between WhatsAppTemplate entity and WhatsAppTemplateModel."""
    
    @staticmethod
    def toEntity(model: WhatsAppTemplateModel) -> WhatsAppTemplate:
        """Convert database model to domain entity.
        
        Args:
            model: WhatsAppTemplateModel from database

        Returns:
            WhatsAppTemplate domain entity
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
            tenant_entity = TenantMapper.toEntity(model.__dict__['tenant'])

        return WhatsAppTemplate(
            id=model.id,
            tenantId=model.tenantId,
            templateName=model.templateName,
            content=model.content,
            serviceName=model.serviceName,
            isActive=model.isActive,
            version=model.version,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt,
            tenant=tenant_entity
        )
    
    @staticmethod
    def toModel(entity: WhatsAppTemplate) -> WhatsAppTemplateModel:
        """Convert domain entity to database model.
        
        Args:
            entity: WhatsAppTemplate domain entity

        Returns:
            WhatsAppTemplateModel for database
        """
        if entity is None:
            return None

        return WhatsAppTemplateModel(
            id=entity.id,
            tenantId=entity.tenantId,
            templateName=entity.templateName,
            content=entity.content,
            serviceName=entity.serviceName,
            isActive=entity.isActive,
            version=entity.version,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[WhatsAppTemplateModel]) -> list[WhatsAppTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of WhatsAppTemplateModel from database

        Returns:
            List of WhatsAppTemplate domain entities
        """
        return [WhatsAppTemplateMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[WhatsAppTemplate]) -> list[WhatsAppTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of WhatsAppTemplate domain entities

        Returns:
            List of WhatsAppTemplateModel for database
        """
        return [WhatsAppTemplateMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: WhatsAppTemplateModel, entity: WhatsAppTemplate) -> WhatsAppTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing WhatsAppTemplateModel
            entity: WhatsAppTemplate with updated data
            
        Returns:
            Updated WhatsAppTemplateModel
        """
        model.tenantId = entity.tenantId
        model.templateName = entity.templateName
        model.content = entity.content
        model.serviceName = entity.serviceName
        model.isActive = entity.isActive
        model.version = entity.version
        model.updatedAt = entity.updatedAt
        
        return model
