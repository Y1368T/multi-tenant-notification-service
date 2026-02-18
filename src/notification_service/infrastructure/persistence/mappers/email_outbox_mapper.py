"""Mapper for EmailOutbox entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel


class EmailOutboxMapper:
    """Mapper for converting between EmailOutbox entity and EmailOutboxModel."""
    
    @staticmethod
    def toEntity(model: EmailOutboxModel) -> EmailOutbox:
        """Convert database model to domain entity.
        
        Args:
            model: EmailOutboxModel from database
            
        Returns:
            EmailOutbox domain entity
        """
        if model is None:
            return None
        
        return EmailOutbox(
            id=model.id,
            recipientEmail=model.recipientEmail,
            messageContent=model.messageContent,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
            retryCount=model.retryCount,
            lastRetryAt=model.lastRetryAt,
            lastErrorMessage=model.lastErrorMessage,
            nextRetryAt=model.nextRetryAt,
            providerAttempted=model.providerAttempted,
            isSent=model.isSent,
            sentAt=model.sentAt,
            status=model.status,
            callbackUrl=model.callbackUrl,
            callbackHeaders=model.callbackHeaders,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
        
    
    @staticmethod
    def toModel(entity: EmailOutbox) -> EmailOutboxModel:
        """Convert domain entity to database model.
        
        Args:
            entity: EmailOutbox domain entity
            
        Returns:
            EmailOutboxModel for database
        """
        if entity is None:
            return None
        
        return EmailOutboxModel(
            id=entity.id,
            recipientEmail=entity.recipientEmail,
            messageContent=entity.messageContent,
            idempotencyKey=entity.idempotencyKey,
            templateId=entity.templateId,
            retryCount=entity.retryCount,
            lastRetryAt=entity.lastRetryAt,
            lastErrorMessage=entity.lastErrorMessage,
            nextRetryAt=entity.nextRetryAt,
            providerAttempted=entity.providerAttempted,
            isSent=entity.isSent,
            sentAt=entity.sentAt,
            status=entity.status,
            callbackUrl=entity.callbackUrl,
            callbackHeaders=entity.callbackHeaders,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[EmailOutboxModel]) -> list[EmailOutbox]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailOutboxModel from database
            
        Returns:
            List of EmailOutbox domain entities
        """
        return [EmailOutboxMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[EmailOutbox]) -> list[EmailOutboxModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of EmailOutbox domain entities
            
        Returns:
            List of EmailOutboxModel for database
        """
        return [EmailOutboxMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: EmailOutboxModel, entity: EmailOutbox) -> EmailOutboxModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailOutboxModel
            entity: EmailOutbox with updated data
            
        Returns:
            Updated EmailOutboxModel
        """
        model.recipientEmail = entity.recipientEmail
        model.messageContent = entity.messageContent
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.retryCount = entity.retryCount
        model.lastRetryAt = entity.lastRetryAt
        model.lastErrorMessage = entity.lastErrorMessage
        model.nextRetryAt = entity.nextRetryAt
        model.providerAttempted = entity.providerAttempted
        model.isSent = entity.isSent
        model.sentAt = entity.sentAt
        model.status = entity.status
        model.callbackUrl = entity.callbackUrl
        model.callbackHeaders = entity.callbackHeaders
        model.updatedAt = entity.updatedAt
        
        return model
