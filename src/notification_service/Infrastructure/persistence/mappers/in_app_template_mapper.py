"""Mapper for InAppTemplate entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper


class InAppTemplateMapper:
    """Mapper for converting between InAppTemplate entity and InAppTemplateModel."""
    
    @staticmethod
    def toEntity(model: InAppTemplateModel) -> InAppTemplate:
        """Convert database model to domain entity.
        
        Args:
            model: InAppTemplateModel from database
            
        Returns:
            InAppTemplate domain entity
        """
        if model is None:
            return None
        
        # Map tenant relationship if loaded (avoid lazy loading)
        tenant_entity = None
        insp = inspect(model)
        if 'tenant' not in insp.unloaded:
            # Relationship is loaded (either already loaded or explicitly eager loaded)
            tenant_model = model.__dict__.get('tenant')
            if tenant_model is not None:
                tenant_entity = TenantMapper.toEntity(tenant_model)
        
        return InAppTemplate(
            id=model.id,
            templateName=model.templateName,
            body=model.body,
            serviceName=model.serviceName,
            tenantId=model.tenantId,
            isActive=model.isActive,
            version=model.version,
            tenant=tenant_entity,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: InAppTemplate) -> InAppTemplateModel:
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
            templateName=entity.templateName,
            body=entity.body,
            serviceName=entity.serviceName,
            tenantId=entity.tenantId,
            isActive=entity.isActive,
            version=entity.version,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[InAppTemplateModel]) -> list[InAppTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of InAppTemplateModel from database
            
        Returns:
            List of InAppTemplate domain entities
        """
        return [InAppTemplateMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[InAppTemplate]) -> list[InAppTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of InAppTemplate domain entities
            
        Returns:
            List of InAppTemplateModel for database
        """
        return [InAppTemplateMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: InAppTemplateModel, entity: InAppTemplate) -> InAppTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing InAppTemplateModel
            entity: InAppTemplate with updated data
            
        Returns:
            Updated InAppTemplateModel
        """
        model.templateName = entity.templateName
        model.body = entity.body
        model.serviceName = entity.serviceName
        model.tenantId = entity.tenantId
        model.isActive = entity.isActive
        model.version = entity.version
        model.updatedAt = entity.updatedAt
        
        return model
