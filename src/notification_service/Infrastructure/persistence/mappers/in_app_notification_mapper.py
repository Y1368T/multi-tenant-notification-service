"""Mapper for InAppNotification entity and model."""
from typing import Optional
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
        
        return InAppNotification(
            id=model.id,
            recipientUserId=model.recipientUserId,
            messageContent=model.messageContent,
            status=model.status,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
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
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.updatedAt = entity.updatedAt
        
        return model
