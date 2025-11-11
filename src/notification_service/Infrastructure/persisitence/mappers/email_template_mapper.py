"""Mapper for EmailTemplate entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.infrastructure.persisitence.models.email.email_template import EmailTemplateModel


class EmailTemplateMapper:
    """Mapper for converting between EmailTemplate entity and EmailTemplateModel."""
    
    @staticmethod
    def toEntity(model: EmailTemplateModel) -> EmailTemplate:
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
            templateName=model.templateName,
            subject=model.subject,
            body=model.body,
            serviceName=model.serviceName,
            tenantId=model.tenantId,
            bodyType=model.bodyType,
            fileUrls=model.fileUrls,
            isActive=model.isActive,
            version=model.version,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: EmailTemplate) -> EmailTemplateModel:
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
            templateName=entity.templateName,
            subject=entity.subject,
            body=entity.body,
            serviceName=entity.serviceName,
            tenantId=entity.tenantId,
            bodyType=entity.bodyType,
            fileUrls=entity.fileUrls,
            isActive=entity.isActive,
            version=entity.version,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[EmailTemplateModel]) -> list[EmailTemplate]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailTemplateModel from database
            
        Returns:
            List of EmailTemplate domain entities
        """
        return [EmailTemplateMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[EmailTemplate]) -> list[EmailTemplateModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of EmailTemplate domain entities
            
        Returns:
            List of EmailTemplateModel for database
        """
        return [EmailTemplateMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: EmailTemplateModel, entity: EmailTemplate) -> EmailTemplateModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailTemplateModel
            entity: EmailTemplate with updated data
            
        Returns:
            Updated EmailTemplateModel
        """
        model.templateName = entity.templateName
        model.subject = entity.subject
        model.body = entity.body
        model.serviceName = entity.serviceName
        model.tenantId = entity.tenantId
        model.bodyType = entity.bodyType
        model.fileUrls = entity.fileUrls
        model.isActive = entity.isActive
        model.version = entity.version
        model.updatedAt = entity.updatedAt
        
        return model
