"""Mapper for EmailNotification entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel


class EmailNotificationMapper:
    """Mapper for converting between EmailNotification entity and EmailNotificationModel."""
    
    @staticmethod
    def toEntity(model: EmailNotificationModel) -> EmailNotification:
        """Convert database model to domain entity.
        
        Args:
            model: EmailNotificationModel from database
            
        Returns:
            EmailNotification domain entity
        """
        if model is None:
            return None
        
        return EmailNotification(
            id=model.id,
            recipientEmail=model.recipientEmail,
            messageContent=model.messageContent,
            status=model.status,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: EmailNotification) -> EmailNotificationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: EmailNotification domain entity
            
        Returns:
            EmailNotificationModel for database
        """
        if entity is None:
            return None
        
        return EmailNotificationModel(
            id=entity.id,
            recipientEmail=entity.recipientEmail,
            messageContent=entity.messageContent,
            status=entity.status,
            idempotencyKey=entity.idempotencyKey,
            templateId=entity.templateId,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
        
    @staticmethod
    def toListOfEntities(models: list[EmailNotificationModel]) -> list[EmailNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailNotificationModel from database
            
        Returns:
            List of EmailNotification domain entities
        """
        return [EmailNotificationMapper.toEntity(model) for model in models]

    @staticmethod
    def toListOfModels(entities: list[EmailNotification]) -> list[EmailNotificationModel]:
        """Convert list of domain entities to list of database models.

        Args:
            entities: List of EmailNotification domain entities

        Returns:
            List of EmailNotificationModel for database
        """
        return [EmailNotificationMapper.toModel(entity) for entity in entities]

    @staticmethod
    def updateModelFromEntity(model: EmailNotificationModel, entity: EmailNotification) -> EmailNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailNotificationModel
            entity: EmailNotification with updated data
            
        Returns:
            Updated EmailNotificationModel
        """
        model.recipientEmail = entity.recipientEmail
        model.messageContent = entity.messageContent
        model.status = entity.status
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.updatedAt = entity.updatedAt
        
        return model
