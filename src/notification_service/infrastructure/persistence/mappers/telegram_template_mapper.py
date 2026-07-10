from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.telegram.telegram_template import TelegramTemplate
from notification_service.infrastructure.persistence.models.telegram.telegram_template import TelegramTemplateModel
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper


class TelegramTemplateMapper:
    """Mapper for converting between TelegramTemplate entity and TelegramTemplateModel."""
    
    @staticmethod
    def toEntity(model: TelegramTemplateModel) -> TelegramTemplate:
        if model is None:
            return None
        
        tenant_entity = None
        insp = inspect(model)
        if 'tenant' in insp.unloaded:
            tenant_entity = None
        elif hasattr(model, 'tenant') and model.__dict__.get('tenant') is not None:
            tenant_entity = TenantMapper.toEntity(model.__dict__['tenant'])

        return TelegramTemplate(
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
    def toModel(entity: TelegramTemplate) -> TelegramTemplateModel:
        if entity is None:
            return None

        return TelegramTemplateModel(
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
    def toListOfEntities(models: list[TelegramTemplateModel]) -> list[TelegramTemplate]:
        return [TelegramTemplateMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TelegramTemplate]) -> list[TelegramTemplateModel]:
        return [TelegramTemplateMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TelegramTemplateModel, entity: TelegramTemplate) -> TelegramTemplateModel:
        model.tenantId = entity.tenantId
        model.templateName = entity.templateName
        model.content = entity.content
        model.serviceName = entity.serviceName
        model.isActive = entity.isActive
        model.version = entity.version
        model.updatedAt = entity.updatedAt
        
        return model
