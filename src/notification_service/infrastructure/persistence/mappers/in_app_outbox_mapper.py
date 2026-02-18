"""Mapper for InAppOutbox entity and model."""
from typing import Optional
from notification_service.domain.entities.in_app.in_app_outbox import InAppOutbox
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel

class InAppOutboxMapper:
    """Mapper for converting between InAppOutbox entity and InAppOutboxModel."""
    
    @staticmethod
    def toEntity(model: InAppOutboxModel) -> InAppOutbox:
        """Convert database model to domain entity."""
        if model is None:
            return None
        
        # Map template if loaded
        template_entity = None
        if hasattr(model, 'template') and model.template:
            from notification_service.infrastructure.persistence.mappers.in_app_template_mapper import InAppTemplateMapper
            template_entity = InAppTemplateMapper.toEntity(model.template)
        
        outbox = InAppOutbox(
            id=model.id,
            templateId=model.templateId,
            recipientUserId=model.recipientUserId,
            messageContent=model.messageContent,
            idempotencyKey=model.idempotencyKey,
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
        
        # Attach template if available
        if template_entity:
            outbox.template = template_entity
        
        return outbox
    
    @staticmethod
    def toModel(entity: InAppOutbox) -> InAppOutboxModel:
        """Convert domain entity to database model."""
        if entity is None:
            return None
        
        return InAppOutboxModel(
            id=entity.id,
            templateId=entity.templateId,
            recipientUserId=entity.recipientUserId,
            messageContent=entity.messageContent,
            idempotencyKey=entity.idempotencyKey,
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
    def toListOfEntities(models: list[InAppOutboxModel]) -> list[InAppOutbox]:
        """Convert list of database models to list of domain entities."""
        return [InAppOutboxMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[InAppOutbox]) -> list[InAppOutboxModel]:
        """Convert list of domain entities to list of database models."""
        return [InAppOutboxMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: InAppOutboxModel, entity: InAppOutbox) -> InAppOutboxModel:
        """Update existing model with entity data."""
        model.templateId = entity.templateId
        model.recipientUserId = entity.recipientUserId
        model.messageContent = entity.messageContent
        model.idempotencyKey = entity.idempotencyKey
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

