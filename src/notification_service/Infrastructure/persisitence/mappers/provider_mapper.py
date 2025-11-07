from notification_service.domain.entities.providers_supported import Provider
from notification_service.Infrastructure.persisitence.models.providers_supported import ProviderModel

class ProviderMapper:
    
    @staticmethod
    def to_entity(model:ProviderModel)->Provider:
        
        if model is None:
            return None
        
        return Provider(
            id=model.id,
            provider_name=model.provider_name,
            display_name=model.display_name,
            config_schema=model.config_schema,
            ui_schema=model.ui_schema,
            channel=model.channel, # sms, email, push, whatsapp
            description=model.description,
            docs_url=model.docs_url,
            test_endpoint=model.test_endpoint,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    @staticmethod
    def to_model(entity: Provider) -> ProviderModel:
        
        if entity is None:
            return None
        
        return ProviderModel(
            id=entity.id,
            provider_name=entity.provider_name,
            display_name=entity.display_name,
            config_schema=entity.config_schema,
            ui_schema=entity.ui_schema,
            channel=entity.channel,
            description=entity.description,
            docs_url=entity.docs_url,
            test_endpoint=entity.test_endpoint,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    
    
    @staticmethod
    def to_list_of_entities(models: list[ProviderModel]) -> list[Provider]:
        """Convert list of database models to list of domain entities.
        
        Args:
            models: List of SMSNotificationModel from database
            
        Returns:
            List of SMSNotification domain entities
        """
        return [ProviderMapper.to_entity(model) for model in models]
    
    @staticmethod
    def to_list_of_models(entities: list[Provider]) -> list[ProviderModel]:
        """Convert list of domain entities to list of database models.
        
        Args:
            entities: List of SMSNotification domain entities
            
        Returns:
            List of SMSNotificationModel for database
        """
        return [ProviderMapper.to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: ProviderModel, entity: Provider) -> ProviderModel:
        
        
        model.channel=entity.channel
        model.description=entity.description
        model.docs_url=entity.docs_url
        model.test_endpoint=entity.test_endpoint
        model.is_active=entity.is_active
        model.updated_at=entity.updated_at
        model.display_name=entity.display_name
        model.name=entity.name
        model.config_schema=entity.config_schema
        model.ui_schema=entity.ui_schema
        model.is_active=entity.is_active
        model.id=entity.id
        model.created_at=entity.created_at
        model.updated_at=entity.updated_at
        
        return model
        