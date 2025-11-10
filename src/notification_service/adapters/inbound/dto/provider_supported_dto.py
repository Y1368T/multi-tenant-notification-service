from pydantic import BaseModel,ConfigDict
from notification_service.domain.entities.providers_supported import Provider
from uuid import uuid4

class TestRequestDto(BaseModel):
    # Define fields for the test request DTO
    address: str
    provider_name: str
    channel: str
    config: dict
    model_config = ConfigDict(from_attributes=True,json_schema_extra={
        "example":{
            "address": "123 Main St",
            "provider_name": "example_provider",
            "channel": "sms",
            "config": {
                "apiKey": "your_api_key",
                "sender": "your_sender_id"
            }
        }
    })

class ProviderSupportedDTO(BaseModel):
    
    provider_name:str
    display_name:str
    channel:str
    description:str
    docs_url:str
    test_endpoint:str
    config_schema:dict
    ui_schema:dict
    is_active:bool
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "provider_name": "ethiotelecom_shortcode",
                "display_name": "EthioTelecom Shortcode",
                "channel": "sms",
                "is_active": True,
                "description": "Send SMS via EthioTelecom shortcode.",
                "docs_url": "https://example.com/docs/ethiotelecom",
                "test_endpoint": "/api/providers/sms/ethiotelecom_shortcode/test",
                "config_schema": {
                    "title": "EthioTelecom Shortcode Configuration",
                    "type": "object",
                    "required": ["apiKey", "shortCode", "senderName", "apiUrl"],
                    "properties": {
                        "apiKey": {"type": "string", "title": "API Key", "minLength": 1},
                        "shortCode": {"type": "string", "title": "Short Code", "minLength": 3},
                        "senderName": {"type": "string", "title": "Sender Name", "minLength": 1},
                        "apiUrl": {"type": "string", "title": "API URL", "format": "uri"}
                    }
                },
                "ui_schema": {
                    "apiKey": {"ui:widget": "password","ui:help": "Enter your API key here.", "ui:placeholder": "API Key"},
                    "shortCode": {"ui:placeholder": "Short Code","ui:help": "Enter the shortcode provided by EthioTelecom.","ui:widget": "text"},
                    "senderName": {"ui:placeholder": "Sender Name","ui:help": "EthioTelecom","ui:widget": "text"},
                    "apiUrl": {"ui:widget": "uri"},
                    "ui:order": ["apiKey", "shortCode", "senderName", "apiUrl"]
                }
            }
        }
    )
    
    def to_entity(self):
        return Provider(
            id=uuid4(),
            provider_name=self.provider_name,
            display_name=self.display_name,
            channel=self.channel,
            description=self.description,
            docs_url=self.docs_url,
            test_endpoint=self.test_endpoint,
            config_schema=self.config_schema,
            ui_schema=self.ui_schema,
            is_active=self.is_active
        )
        