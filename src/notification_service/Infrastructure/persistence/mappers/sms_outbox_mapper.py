"""Mapper for SMSOutbox entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel


class SmsOutboxMapper:
    """Mapper for converting between SMSOutbox entity and SmsOutboxModel."""
    
    @staticmethod
    def toEntity(model: SmsOutboxModel) -> SMSOutbox:
        """Convert database model to domain entity.
        
        Args:
            model: SmsOutboxModel from database
            
        Returns:
            SMSOutbox domain entity
        """
        if model is None:
            return None
        
        # Import here to avoid circular dependency
        from notification_service.infrastructure.persistence.mappers.sms_template_mapper import SmsTemplateMapper
        
        # Extract template if loaded
        template_entity = None
        insp = inspect(model)
        
        # Check if template is loaded without triggering lazy load
        if 'template' not in insp.unloaded:
            template_model = model.__dict__.get('template')
            if template_model is not None:
                # Map the template model to entity
                template_entity = SmsTemplateMapper.toEntity(template_model)
        
        return SMSOutbox(
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
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: SMSOutbox) -> SmsOutboxModel:
        """Convert domain entity to database model.
        
        Args:
            entity: SMSOutbox domain entity
            
        Returns:
            SmsOutboxModel for database
        """
        if entity is None:
            return None
        
        return SmsOutboxModel(
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
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[SmsOutboxModel]) -> list[SMSOutbox]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SmsOutboxModel from database
            
        Returns:
            List of SMSOutbox domain entities
        """
        return [SmsOutboxMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[SMSOutbox]) -> list[SmsOutboxModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSOutbox domain entities
            
        Returns:
            List of SmsOutboxModel for database
        """
        return [SmsOutboxMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: SmsOutboxModel, entity: SMSOutbox) -> SmsOutboxModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SmsOutboxModel
            entity: SMSOutbox with updated data
            
        Returns:
            Updated SmsOutboxModel
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
        model.updatedAt = entity.updatedAt
        
        return model
