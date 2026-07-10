from typing import Optional
from sqlalchemy import inspect
from notification_service.domain.entities.telegram.telegram_outbox import TelegramOutbox
from notification_service.infrastructure.persistence.models.telegram.telegram_outbox import TelegramOutboxModel
from notification_service.infrastructure.persistence.mappers.telegram_template_mapper import TelegramTemplateMapper


class TelegramOutboxMapper:
    """Mapper for converting between TelegramOutbox entity and TelegramOutboxModel."""
    
    @staticmethod
    def toEntity(model: TelegramOutboxModel) -> TelegramOutbox:
        if model is None:
            return None
        
        template_entity = None
        insp = inspect(model)
        if 'template' in insp.unloaded:
            template_entity = None
        elif hasattr(model, 'template') and model.__dict__.get('template') is not None:
            template_entity = TelegramTemplateMapper.toEntity(model.__dict__['template'])

        return TelegramOutbox(
            id=model.id,
            recipientChatId=model.recipientChatId,
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
            callbackUrl=model.callbackUrl,
            callbackHeaders=model.callbackHeaders,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    
    @staticmethod
    def toModel(entity: TelegramOutbox) -> TelegramOutboxModel:
        if entity is None:
            return None

        return TelegramOutboxModel(
            id=entity.id,
            templateId=entity.templateId,
            recipientChatId=entity.recipientChatId,
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
    def toListOfEntities(models: list[TelegramOutboxModel]) -> list[TelegramOutbox]:
        return [TelegramOutboxMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[TelegramOutbox]) -> list[TelegramOutboxModel]:
        return [TelegramOutboxMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: TelegramOutboxModel, entity: TelegramOutbox) -> TelegramOutboxModel:
        model.templateId = entity.templateId
        model.recipientChatId = entity.recipientChatId
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
