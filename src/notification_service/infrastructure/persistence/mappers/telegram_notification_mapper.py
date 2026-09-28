from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.telegram.telegram_notification import TelegramNotification
from notification_service.infrastructure.persistence.models.telegram.telegram_notification import TelegramNotificationModel
from notification_service.infrastructure.persistence.mappers.telegram_template_mapper import TelegramTemplateMapper


class TelegramNotificationMapper:
    """Mapper for converting between TelegramNotification entity and TelegramNotificationModel."""
    
    @staticmethod
    def toEntity(model: TelegramNotificationModel) -> TelegramNotification:
        if model is None:
            return None
        
        template_entity = None
        insp = inspect(model)
        if 'template' in insp.unloaded:
            template_entity = None
        elif hasattr(model, 'template') and model.__dict__.get('template') is not None:
            template_entity = TelegramTemplateMapper.toEntity(model.__dict__['template'])

        return TelegramNotification(
            id=model.id,
            recipientChatId=model.recipientChatId,
            messageContent=model.messageContent,
            status=model.status,
            isRead=model.isRead,
            externalId=model.externalId,
            idempotencyKey=model.idempotencyKey,
            templateId=model.templateId,
            template=template_entity,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TelegramNotification) -> TelegramNotificationModel:
        if entity is None:
            return None

        return TelegramNotificationModel(
            id=entity.id,
            recipientChatId=entity.recipientChatId,
            messageContent=entity.messageContent,
            status=entity.status,
            isRead=entity.isRead,
            externalId=entity.externalId,
            idempotencyKey=entity.idempotencyKey,
            templateId=entity.templateId,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    @staticmethod
    def toListOfEntities(models: list[TelegramNotificationModel]) -> list[TelegramNotification]:
        return [TelegramNotificationMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TelegramNotification]) -> list[TelegramNotificationModel]:
        return [TelegramNotificationMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TelegramNotificationModel, entity: TelegramNotification) -> TelegramNotificationModel:
        model.recipientChatId = entity.recipientChatId
        model.messageContent = entity.messageContent
        model.status = entity.status
        model.isRead = entity.isRead
        model.externalId = entity.externalId
        model.idempotencyKey = entity.idempotencyKey
        model.templateId = entity.templateId
        model.updatedAt = entity.updatedAt
        
        return model
