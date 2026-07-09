"""Mapper for SMSOutbox entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.whatsapp.whatsapp_outbox import WhatsAppOutbox
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel


class WhatsAppOutboxMapper:
    """Mapper for converting between SMSOutbox entity and SmsOutboxModel."""
    
    @staticmethod
    def toEntity(model: WhatsAppOutboxModel) -> WhatsAppOutbox:
        """Convert database model to domain entity.
        
        Args:
            model: WhatsAppOutboxModel from database
            
        Returns:
            WhatsAppOutbox domain entity
        """
        if model is None:
            return None
        
        # Import here to avoid circular dependency
        from notification_service.infrastructure.persistence.mappers.whatsapp.whatsapp_template_mapper import WhatsAppTemplateMapper
        
        # Extract template if loaded
        template_entity = None
        insp = inspect(model)
        
        # Check if template is loaded without triggering lazy load
        if 'template' not in insp.unloaded:
            template_model = model.__dict__.get('template')
            if template_model is not None:
                # Map the template model to entity
                template_entity = WhatsAppTemplateMapper.toEntity(template_model)
        
        return WhatsAppOutbox(
            id=model.id,
            recipientNumber=model.recipientNumber,
            messageContent=model.messageContent,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
            template=template_entity,
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
    def toModel(entity: WhatsAppOutbox) -> WhatsAppOutboxModel:
        """Convert domain entity to database model.
        
        Args:
            entity: WhatsAppOutbox domain entity
            
        Returns:
            WhatsAppOutboxModel for database
        """
        if entity is None:
            return None
        
        return WhatsAppOutboxModel(
            id=entity.id,
            recipientNumber=entity.recipientNumber,
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
    def toListOfEntities(models: list[WhatsAppOutboxModel]) -> list[WhatsAppOutbox]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of WhatsAppOutboxModel from database
            
        Returns:
            List of WhatsAppOutbox domain entities
        """
        return [WhatsAppOutboxMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[WhatsAppOutbox]) -> list[WhatsAppOutboxModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of WhatsAppOutbox domain entities
            
        Returns:
            List of WhatsAppOutboxModel for database
        """
        return [WhatsAppOutboxMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: WhatsAppOutboxModel, entity: WhatsAppOutbox) -> WhatsAppOutboxModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing WhatsAppOutboxModel
            entity: WhatsAppOutbox with updated data
            
        Returns:
            Updated WhatsAppOutboxModel
        """
        model.recipientNumber = entity.recipientNumber
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
