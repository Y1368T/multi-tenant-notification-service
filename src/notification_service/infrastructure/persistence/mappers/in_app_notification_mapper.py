"""Mapper for InAppNotification entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel


class InAppNotificationMapper:
    """Mapper for converting between InAppNotification entity and InAppNotificationModel."""
    
    @staticmethod
    def toEntity(model: InAppNotificationModel) -> InAppNotification:
        """Convert database model to domain entity.
        
        Args:
            model: InAppNotificationModel from database
            
        Returns:
            InAppNotification domain entity
        """
        if model is None:
            return None
        
        # Import here to avoid circular dependency
        from notification_service.infrastructure.persistence.mappers.in_app_template_mapper import InAppTemplateMapper
        
        # Extract template if loaded
        template_entity = None
        template_name = None
        insp = inspect(model)
        
        # Check if template is loaded without triggering lazy load
        if 'template' not in insp.unloaded:
            template_model = model.__dict__.get('template')
            if template_model is not None:
                # Map the template model to entity
                template_entity = InAppTemplateMapper.toEntity(template_model)
                # Extract template name
                template_name = template_entity.templateName if template_entity else None
        
        return InAppNotification(
            id=model.id,
            recipientUserId=model.recipientUserId,
            messageContent=model.messageContent,
            status=model.status,
            isRead=model.isRead if hasattr(model, 'isRead') else False,
            externalId=model.externalId if hasattr(model, 'externalId') else None,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
            template=template_entity,
            templateName=template_name,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: InAppNotification) -> InAppNotificationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: InAppNotification domain entity
            
        Returns:
            InAppNotificationModel for database
        """
        if entity is None:
            return None
        
        return InAppNotificationModel(
            id=entity.id,
            recipientUserId=entity.recipientUserId,
            messageContent=entity.messageContent,
            status=entity.status,
            isRead=entity.isRead if hasattr(entity, 'isRead') else False,
            externalId=entity.externalId if hasattr(entity, 'externalId') else None,
            idempotencyKey=entity.idempotencyKey,
            templateId=entity.templateId,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[InAppNotificationModel]) -> list[InAppNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of InAppNotificationModel from database
            
        Returns:
            List of InAppNotification domain entities
        """
        return [InAppNotificationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[InAppNotification]) -> list[InAppNotificationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of InAppNotification domain entities
            
        Returns:
            List of InAppNotificationModel for database
        """
        return [InAppNotificationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: InAppNotificationModel, entity: InAppNotification) -> InAppNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing InAppNotificationModel
            entity: InAppNotification with updated data
            
        Returns:
            Updated InAppNotificationModel
        """
        model.recipientUserId = entity.recipientUserId
        model.messageContent = entity.messageContent
        model.status = entity.status
        model.isRead = entity.isRead if hasattr(entity, 'isRead') else model.isRead
        model.externalId = entity.externalId if hasattr(entity, 'externalId') else model.externalId
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.updatedAt = entity.updatedAt
        
        return model
