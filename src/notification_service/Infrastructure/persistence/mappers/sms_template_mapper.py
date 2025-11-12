"""Mapper for SmsTemplate entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper
           

class SmsTemplateMapper:
    """Mapper for converting between SmsTemplate entity and SmsTemplateModel."""
    
    @staticmethod
    def toEntity(model: SmsTemplateModel) -> SmsTemplate:
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
            tenant_entity = TenantMapper.toEntity(model.__dict__['tenant'])

        return SmsTemplate(
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
    def toModel(entity: SmsTemplate) -> SmsTemplateModel:
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
    def toListOfEntities(models: list[SmsTemplateModel]) -> list[SmsTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SmsTemplateModel from database

        Returns:
            List of SmsTemplate domain entities
        """
        return [SmsTemplateMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[SmsTemplate]) -> list[SmsTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SmsTemplate domain entities

        Returns:
            List of SmsTemplateModel for database
        """
        return [SmsTemplateMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: SmsTemplateModel, entity: SmsTemplate) -> SmsTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SmsTemplateModel
            entity: SmsTemplate with updated data
            
        Returns:
            Updated SmsTemplateModel
        """
        model.tenantId = entity.tenantId
        model.templateName = entity.templateName
        model.content = entity.content
        model.serviceName = entity.serviceName
        model.isActive = entity.isActive
        model.version = entity.version
        model.updatedAt = entity.updatedAt
        
        return model
