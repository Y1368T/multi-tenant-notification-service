"""Mapper for WhatsAppNotification entity and model."""
from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.whatsapp.whatsapp_notification import WhatsAppNotification
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel


class WhatsAppNotificationMapper:
    """Mapper for converting between WhatsAppNotification entity and WhatsAppNotificationModel."""
    
    @staticmethod
    def toEntity(model: WhatsAppNotificationModel) -> WhatsAppNotification:
        """Convert database model to domain entity.
        
        Args:
            model: WhatsAppNotificationModel from database
            
        Returns:
            WhatsAppNotification domain entity
        """
        if model is None:
            return None
        
        # Import here to avoid circular dependency
        from notification_service.infrastructure.persistence.mappers.whatsapp.whatsapp_template_mapper import WhatsAppTemplateMapper
        
        # Extract template if loaded
        template_entity = None
        template_name = None
        insp = inspect(model)
        
        # Check if template is loaded without triggering lazy load
        if 'template' not in insp.unloaded:
            template_model = model.__dict__.get('template')
            if template_model is not None:
                # Map the template model to entity
                template_entity = WhatsAppTemplateMapper.toEntity(template_model)
                # Extract template name from template entity
                if template_entity and hasattr(template_entity, 'templateName'):
                    template_name = template_entity.templateName
        
        return WhatsAppNotification(
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
    def toModel(entity: WhatsAppNotification) -> WhatsAppNotificationModel:
        """Convert domain entity to database model.
        
        Args:
            entity: WhatsAppNotification domain entity
            
        Returns:
            WhatsAppNotificationModel for database
        """
        if entity is None:
            return None
        
        return WhatsAppNotificationModel(
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
    def toListOfEntities(models: list[WhatsAppNotificationModel]) -> list[WhatsAppNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of WhatsAppNotificationModel from database
            
        Returns:
            List of WhatsAppNotification domain entities
        """
        return [SMSNotificationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[WhatsAppNotification]) -> list[WhatsAppNotificationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of WhatsAppNotification domain entities
            
        Returns:
            List of WhatsAppNotificationModel for database
        """
        return [WhatsAppNotificationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: WhatsAppNotificationModel, entity: WhatsAppNotification) -> WhatsAppNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing WhatsAppNotificationModel
            entity: WhatsAppNotification with updated data
            
        Returns:
            Updated WhatsAppNotificationModel
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
