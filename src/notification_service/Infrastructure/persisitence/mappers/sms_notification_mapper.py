"""Mapper for SMSNotification entity and model."""
from typing import Optional
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.Infrastructure.persisitence.models.sms.sms_notification import SMSNotificationModel


class SmsNotificationMapper:
    """Mapper for converting between SMSNotification entity and SMSNotificationModel."""
    
    @staticmethod
    def to_entity(model: SMSNotificationModel) -> SMSNotification:
        """Convert database model to domain entity.
        
        Args:
            model: SMSNotificationModel from database
            
        Returns:
            SMSNotification domain entity
        """
        if model is None:
            return None
        
        return SMSNotification(
            id=model.id,
            recipient_number=model.recipient_number,
            message_content=model.message_content,
            status=model.status,
            idempotency_key=model.idempotency_key,
            template_id=model.template_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            # templateName=model.template.template_name
        )
    
    @staticmethod
    def to_model(entity: SMSNotification) -> SMSNotificationModel:
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
            recipient_number=entity.recipient_number,
            message_content=entity.message_content,
            status=entity.status,
            idempotency_key=entity.idempotency_key,
            template_id=entity.template_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[SMSNotificationModel]) -> list[SMSNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SMSNotificationModel from database
            
        Returns:
            List of SMSNotification domain entities
        """
        return [SmsNotificationMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[SMSNotification]) -> list[SMSNotificationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSNotification domain entities
            
        Returns:
            List of SMSNotificationModel for database
        """
        return [SmsNotificationMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: SMSNotificationModel, entity: SMSNotification) -> SMSNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SMSNotificationModel
            entity: SMSNotification with updated data
            
        Returns:
            Updated SMSNotificationModel
        """
        model.recipient_number = entity.recipient_number
        model.message_content = entity.message_content
        model.status = entity.status
        model.idempotency_key = entity.idempotency_key
        model.template_id = entity.template_id
        model.updated_at = entity.updated_at
        
        return model
