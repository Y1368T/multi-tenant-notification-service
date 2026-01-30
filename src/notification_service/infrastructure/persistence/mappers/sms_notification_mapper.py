"""Mapper for SMSNotification entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel


class SmsNotificationMapper:
    """Mapper for converting between SMSNotification entity and SMSNotificationModel."""
    
    @staticmethod
    def toEntity(model: SMSNotificationModel) -> SMSNotification:
        """Convert database model to domain entity.
        
        Args:
            model: SMSNotificationModel from database
            
        Returns:
            SMSNotification domain entity
        """
        if model is None:
            return None
        
        # Import here to avoid circular dependency
        from notification_service.infrastructure.persistence.mappers.sms_template_mapper import SmsTemplateMapper
        
        # Extract template if loaded
        template_entity = None
        template_name = None
        insp = inspect(model)
        
        # Check if template is loaded without triggering lazy load
        if 'template' not in insp.unloaded:
            template_model = model.__dict__.get('template')
            if template_model is not None:
                # Map the template model to entity
                template_entity = SmsTemplateMapper.toEntity(template_model)
                # Extract template name from template entity
                if template_entity and hasattr(template_entity, 'templateName'):
                    template_name = template_entity.templateName
        
        return SMSNotification(
            id=model.id,
            recipientNumber=model.recipientNumber,
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
    def toModel(entity: SMSNotification) -> SMSNotificationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: SMSNotification domain entity
            
        Returns:
            SMSNotificationModel for database
        """
        if entity is None:
            return None
        
        return SMSNotificationModel(
            id=entity.id,
            recipientNumber=entity.recipientNumber,
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
    def toListOfEntities(models: list[SMSNotificationModel]) -> list[SMSNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SMSNotificationModel from database
            
        Returns:
            List of SMSNotification domain entities
        """
        return [SmsNotificationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[SMSNotification]) -> list[SMSNotificationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSNotification domain entities
            
        Returns:
            List of SMSNotificationModel for database
        """
        return [SmsNotificationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: SMSNotificationModel, entity: SMSNotification) -> SMSNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SMSNotificationModel
            entity: SMSNotification with updated data
            
        Returns:
            Updated SMSNotificationModel
        """
        model.recipientNumber = entity.recipientNumber
        model.messageContent = entity.messageContent
        model.status = entity.status
        model.isRead = entity.isRead if hasattr(entity, 'isRead') else model.isRead
        model.externalId = entity.externalId if hasattr(entity, 'externalId') else model.externalId
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.updatedAt = entity.updatedAt
        
        return model
