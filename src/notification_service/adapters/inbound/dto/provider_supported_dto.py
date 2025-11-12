from pydantic import BaseModel, ConfigDict, Field
from notification_service.domain.entities.providers_supported import Provider
from uuid import uuid4, UUID
from typing import Optional, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO

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
    
    providerName: str = Field(alias="provider_name")
    displayName: str = Field(alias="display_name")
    channel: str
    description: str
    docsUrl: str = Field(alias="docs_url")
    testEndpoint: str = Field(alias="test_endpoint")
    configSchema: dict = Field(alias="config_schema")
    uiSchema: dict = Field(alias="ui_schema")
    isActive: bool = Field(alias="is_active")
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=False,
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
    
    def toEntity(self):
        return Provider(
            id=uuid4(),
            providerName=self.providerName,
            displayName=self.displayName,
            channel=self.channel,
            description=self.description,
            docsUrl=self.docsUrl,
            testEndpoint=self.testEndpoint,
            configSchema=self.configSchema,
            uiSchema=self.uiSchema,
            isActive=self.isActive
        )


class ProviderResponseDTO(BaseModel):
    """Response DTO for providers."""
    id: UUID
    providerName: str = Field(alias="provider_name")
    displayName: str = Field(alias="display_name")
    channel: str
    description: Optional[str] = None
    docsUrl: Optional[str] = Field(None, alias="docs_url")
    testEndpoint: Optional[str] = Field(None, alias="test_endpoint")
    configSchema: Dict[str, Any] = Field(default_factory=dict, alias="config_schema")
    uiSchema: Optional[Dict[str, Any]] = Field(None, alias="ui_schema")
    isActive: bool = Field(alias="is_active")
    createdAt: datetime = Field(alias="created_at")
    updatedAt: datetime = Field(alias="updated_at")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, provider: Provider):
        """Create DTO from entity with related data."""
        return cls(
            id=provider.id,
            providerName=provider.providerName,
            displayName=provider.displayName,
            channel=provider.channel,
            description=provider.description,
            docsUrl=provider.docsUrl,
            testEndpoint=provider.testEndpoint,
            configSchema=provider.configSchema,
            uiSchema=provider.uiSchema,
            isActive=provider.isActive,
            createdAt=provider.createdAt,
            updatedAt=provider.updatedAt
        )


class ProviderFilterDTO(PaginatedRequestDTO):
    """Filter DTO for provider queries with custom filters."""
    channel: Optional[str] = Field(None, description="Filter by channel (sms, email, etc.)")
    isActive: Optional[bool] = Field(None, alias="is_active", description="Filter by active status")
        