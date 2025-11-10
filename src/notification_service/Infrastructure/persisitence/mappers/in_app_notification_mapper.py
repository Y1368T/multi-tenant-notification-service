"""Mapper for InAppNotification entity and model."""
from typing import Optional
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.infrastructure.persisitence.models.in_app.in_app_notification import InAppNotificationModel


class InAppNotificationMapper:
    """Mapper for converting between InAppNotification entity and InAppNotificationModel."""
    
    @staticmethod
    def to_entity(model: InAppNotificationModel) -> InAppNotification:
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
            recipient_user_id=model.recipient_user_id,
            message_content=model.message_content,
            status=model.status,
            idempotency_key=model.idempotency_key,
            template_id=model.template_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @staticmethod
    def to_model(entity: InAppNotification) -> InAppNotificationModel:
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
            recipient_user_id=entity.recipient_user_id,
            message_content=entity.message_content,
            status=entity.status,
            idempotency_key=entity.idempotency_key,
            template_id=entity.template_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[InAppNotificationModel]) -> list[InAppNotification]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of InAppNotificationModel from database
            
        Returns:
            List of InAppNotification domain entities
        """
        return [InAppNotificationMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[InAppNotification]) -> list[InAppNotificationModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of InAppNotification domain entities
            
        Returns:
            List of InAppNotificationModel for database
        """
        return [InAppNotificationMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: InAppNotificationModel, entity: InAppNotification) -> InAppNotificationModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing InAppNotificationModel
            entity: InAppNotification with updated data
            
        Returns:
            Updated InAppNotificationModel
        """
        model.recipient_user_id = entity.recipient_user_id
        model.message_content = entity.message_content
        model.status = entity.status
        model.idempotency_key = entity.idempotency_key
        model.template_id = entity.template_id
        model.updated_at = entity.updated_at
        
        return model
