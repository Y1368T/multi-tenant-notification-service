"""Mapper for SMSOutbox entity and model."""
from typing import Optional
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.infrastructure.persisitence.models.sms.sms_outbox import SmsOutboxModel


class SmsOutboxMapper:
    """Mapper for converting between SMSOutbox entity and SmsOutboxModel."""
    
    @staticmethod
    def to_entity(model: SmsOutboxModel) -> SMSOutbox:
        """Convert database model to domain entity.
        
        Args:
            model: SmsOutboxModel from database
            
        Returns:
            SMSOutbox domain entity
        """
        if model is None:
            return None
        
        return SMSOutbox(
            id=model.id,
            recipient_number=model.recipient_number,
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
    def to_model(entity: SMSOutbox) -> SmsOutboxModel:
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
            recipient_number=entity.recipient_number,
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
    def to_list_of_entities(models: list[SmsOutboxModel]) -> list[SMSOutbox]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SmsOutboxModel from database
            
        Returns:
            List of SMSOutbox domain entities
        """
        return [SmsOutboxMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[SMSOutbox]) -> list[SmsOutboxModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSOutbox domain entities
            
        Returns:
            List of SmsOutboxModel for database
        """
        return [SmsOutboxMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: SmsOutboxModel, entity: SMSOutbox) -> SmsOutboxModel:
        """Update existing model with entity data.
        
        Args:
            model: Existing SmsOutboxModel
            entity: SMSOutbox with updated data
            
        Returns:
            Updated SmsOutboxModel
        """
        model.recipient_number = entity.recipient_number
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
