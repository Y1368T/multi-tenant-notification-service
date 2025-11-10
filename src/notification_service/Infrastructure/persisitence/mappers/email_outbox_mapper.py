"""Mapper for EmailOutbox entity and model."""
from typing import Optional
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.infrastructure.persisitence.models.email.email_outbox import EmailOutboxModel


class EmailOutboxMapper:
    """Mapper for converting between EmailOutbox entity and EmailOutboxModel."""
    
    @staticmethod
    def to_entity(model: EmailOutboxModel) -> EmailOutbox:
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
            recipient_email=model.recipient_email,
            message_content=model.message_content,
            idempotency_key=model.idempotency_key,
            template_id=model.template_id,
            retry_count=model.retry_count,
            last_retry_at=model.last_retry_at,
            last_error_message=model.last_error_message,
            next_retry_at=model.next_retry_at,
            provider_attempted=model.provider_attempted,
            is_sent=model.is_sent,
            sent_at=model.sent_at,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
        
    
    @staticmethod
    def to_model(entity: EmailOutbox) -> EmailOutboxModel:
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
            recipient_email=entity.recipient_email,
            message_content=entity.message_content,
            idempotency_key=entity.idempotency_key,
            template_id=entity.template_id,
            retry_count=entity.retry_count,
            last_retry_at=entity.last_retry_at,
            last_error_message=entity.last_error_message,
            next_retry_at=entity.next_retry_at,
            provider_attempted=entity.provider_attempted,
            is_sent=entity.is_sent,
            sent_at=entity.sent_at,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def to_list_of_entities(models: list[EmailOutboxModel]) -> list[EmailOutbox]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of EmailOutboxModel from database
            
        Returns:
            List of EmailOutbox domain entities
        """
        return [EmailOutboxMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[EmailOutbox]) -> list[EmailOutboxModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of EmailOutbox domain entities
            
        Returns:
            List of EmailOutboxModel for database
        """
        return [EmailOutboxMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: EmailOutboxModel, entity: EmailOutbox) -> EmailOutboxModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing EmailOutboxModel
            entity: EmailOutbox with updated data
            
        Returns:
            Updated EmailOutboxModel
        """
        model.recipient_email = entity.recipient_email
        model.message_content = entity.message_content
        model.idempotency_key = entity.idempotency_key
        model.template_id = entity.template_id
        model.retry_count = entity.retry_count
        model.last_retry_at = entity.last_retry_at
        model.last_error_message = entity.last_error_message
        model.next_retry_at = entity.next_retry_at
        model.provider_attempted = entity.provider_attempted
        model.is_sent = entity.is_sent
        model.sent_at = entity.sent_at
        model.status = entity.status
        model.updated_at = entity.updated_at
        
        return model
