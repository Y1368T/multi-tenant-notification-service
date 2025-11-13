from notification_service.domain.entities.providers_supported import Provider
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel

class ProviderMapper:
    
    @staticmethod
    def toEntity(model:ProviderModel)->Provider:
        
        if model is None:
            return None
        
        return Provider(
            id=model.id,
            providerName=model.providerName,
            displayName=model.displayName,
            configSchema=model.configSchema,
            uiSchema=model.uiSchema,
            channel=model.channel, # sms, email, push, whatsapp
            description=model.description,
            docsUrl=model.docsUrl,
            testEndpoint=model.testEndpoint,
            isActive=model.isActive,
            createdAt=model.createdAt,
            updatedAt=model.updatedAt
        )
    @staticmethod
    def toModel(entity: Provider) -> ProviderModel:
        
        if entity is None:
            return None
        
        return ProviderModel(
            id=entity.id,
            providerName=entity.providerName,
            displayName=entity.displayName,
            configSchema=entity.configSchema,
            uiSchema=entity.uiSchema,
            channel=entity.channel,
            description=entity.description,
            docsUrl=entity.docsUrl,
            testEndpoint=entity.testEndpoint,
            isActive=entity.isActive,
            createdAt=entity.createdAt,
            updatedAt=entity.updatedAt
        )
    
    
    
    @staticmethod
    def toListOfEntities(models: list[ProviderModel]) -> list[Provider]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SMSNotificationModel from database
            
        Returns:
            List of SMSNotification domain entities
        """
        return [ProviderMapper.toEntity(model) for model in models]
    
    @staticmethod
    def toListOfModels(entities: list[Provider]) -> list[ProviderModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSNotification domain entities
            
        Returns:
            List of SMSNotificationModel for database
        """
        return [ProviderMapper.toModel(entity) for entity in entities]
    
    @staticmethod
    def updateModelFromEntity(model: ProviderModel, entity: Provider) -> ProviderModel:
        
        
        model.channel=entity.channel
        model.description=entity.description
        model.docsUrl=entity.docsUrl
        model.testEndpoint=entity.testEndpoint
        model.isActive=entity.isActive
        model.updatedAt=entity.updatedAt
        model.displayName=entity.displayName
        model.providerName=entity.providerName
        model.configSchema=entity.configSchema
        model.uiSchema=entity.uiSchema
        model.isActive=entity.isActive
        model.id=entity.id
        model.createdAt=entity.createdAt
        model.updatedAt=entity.updatedAt
        
        return model
        