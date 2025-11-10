"""Mapper for EmailNotification entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.infrastructure.persisitence.models.email.email_notification import EmailNotificationModel


class EmailNotificationMapper:
    """Mapper for converting between EmailNotification entity and EmailNotificationModel."""
    
    @staticmethod
    def to_entity(model: EmailNotificationModel) -> EmailNotification:
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
            recipient_email=model.recipient_email,
            message_content=model.message_content,
            status=model.status,
            idempotency_key=model.idempotency_key,
            template_id=model.template_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: EmailNotification) -> EmailNotificationModel:
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
            recipient_email=entity.recipient_email,
            message_content=entity.message_content,
            status=entity.status,
            idempotency_key=entity.idempotency_key,
            template_id=entity.template_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
        
    @staticmethod
    def to_list_of_entities(models: list[EmailNotificationModel]) -> list[EmailNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailNotificationModel from database
            
        Returns:
            List of EmailNotification domain entities
        """
        return [EmailNotificationMapper.to_entity(model) for model in models]

    @staticmethod
    def to_list_of_models(entities: list[EmailNotification]) -> list[EmailNotificationModel]:
        """Convert list of domain entities to list of database models.

        Args:
            entities: List of EmailNotification domain entities

        Returns:
            List of EmailNotificationModel for database
        """
        return [EmailNotificationMapper.to_model(entity) for entity in entities]

    @staticmethod
    def update_model_from_entity(model: EmailNotificationModel, entity: EmailNotification) -> EmailNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailNotificationModel
            entity: EmailNotification with updated data
            
        Returns:
            Updated EmailNotificationModel
        """
        model.recipient_email = entity.recipient_email
        model.message_content = entity.message_content
        model.status = entity.status
        model.idempotency_key = entity.idempotency_key
        model.template_id = entity.template_id
        model.updated_at = entity.updated_at
        
        return model
