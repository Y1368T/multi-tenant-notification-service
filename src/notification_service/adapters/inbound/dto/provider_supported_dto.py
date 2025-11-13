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
                "provider_name": "afromessage",
                "display_name": "Afromessage",
                "channel": "sms",
                "is_active": True,
                "description": "Send SMS via Afromessage API.",
                "docs_url": "https://example.com/docs/afromessage",
                "test_endpoint": "/api/providers/sms/afromessage/test",
                "config_schema": {
                    "title": "Afromessage Configuration",
                    "type": "object",
                    "required": ["baseUrl", "apiKey", "sender", "from"],
                    "properties": {
                        "baseUrl": {"type": "string", "title": "Base URL", "format": "uri", "default": "https://api.afromessage.com/api"},
                        "apiKey": {"type": "string", "title": "API Key", "minLength": 1},
                        "sender": {"type": "string", "title": "Sender Name", "minLength": 1},
                        "from": {"type": "string", "title": "From ID", "minLength": 1},
                        "callbackUrl": {"type": "string", "title": "Callback URL", "format": "uri"}
                    }
                },
                "ui_schema": {
                    "baseUrl": {"ui:widget": "uri", "ui:help": "Enter the Afromessage API base URL.", "ui:placeholder": "https://api.afromessage.com/api"},
                    "apiKey": {"ui:widget": "password", "ui:help": "Enter your Afromessage API key here.", "ui:placeholder": "API Key"},
                    "sender": {"ui:placeholder": "Sender Name", "ui:help": "Enter the sender name for SMS.", "ui:widget": "text"},
                    "from": {"ui:placeholder": "From ID", "ui:help": "Enter the from ID provided by Afromessage.", "ui:widget": "text"},
                    "callbackUrl": {"ui:widget": "uri", "ui:help": "Optional callback URL for delivery status.", "ui:placeholder": "https://your-domain.com/callback"},
                    "ui:order": ["baseUrl", "apiKey", "sender", "from", "callbackUrl"]
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
        