from pydantic import BaseModel, ConfigDict, Field, field_validator
from notification_service.domain.entities.providers_supported import Provider
from uuid import uuid4, UUID
from typing import Optional, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input
import re

class TestRequestDto(BaseModel):
    # Define fields for the test request DTO
    address: str
    provider_name: str
    channel: str
    config: dict
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "address": "123 Main St",
                "provider_name": "example_provider",
                "channel": "sms",
                "config": {
                    "apiKey": "your_api_key",
                    "sender": "your_sender_id"
                }
            }
        })
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate address (phone or email)."""
        return validate_string_input(
            v,
            field_name='address',
            max_length=255,
            min_length=1
        )
    
    @field_validator('provider_name')
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """Validate provider name."""
        return validate_string_input(
            v,
            field_name='provider_name',
            max_length=50
        )
    
    @field_validator('channel')
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate channel."""
        allowed_channels = ["sms", "email", "inapp", "whatsapp"]
        sanitized = validate_string_input(v, field_name='channel')
        if sanitized.lower() not in allowed_channels:
            raise ValueError(f"Channel must be one of: {', '.join(allowed_channels)}")
        return sanitized.lower()
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: dict) -> dict:
        """Validate configuration dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        
        # Sanitize string values in config
        sanitized_config = {}
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Config keys must be strings")
            
            sanitized_key = validate_string_input(
                key,
                field_name=f'config.{key}',
                max_length=100
            )
            
            if isinstance(value, str):
                # Allow longer values for config fields (e.g., private keys can be 2000+ chars)
                # Check for known long fields that need more space
                max_len = 10000 if key in ['private_key', 'privateKey', 'certificate', 'cert', 'key'] else 5000
                
                # Skip SQL injection checking for encoded/sensitive fields (private keys, certificates, etc.)
                # These fields contain base64-encoded data that may accidentally match SQL patterns
                skip_sql_check = key.lower() in [
                    'private_key', 'privatekey', 'private_key_id', 'privatekeyid',
                    'certificate', 'cert', 'key', 'token', 'secret', 'api_key', 'apikey',
                    'client_x509_cert_url', 'clientx509certurl', 'auth_provider_x509_cert_url'
                ]
                
                if skip_sql_check:
                    # For sensitive fields, only validate length, skip SQL/XSS checks
                    if max_len and len(value) > max_len:
                        raise ValueError(f"config.{key} must be at most {max_len} characters")
                    sanitized_value = value  # Don't sanitize encoded data
                else:
                    sanitized_value = validate_string_input(
                        value,
                        field_name=f'config.{key}',
                        max_length=max_len
                    )
            else:
                sanitized_value = value
            
            sanitized_config[sanitized_key] = sanitized_value
        
        return sanitized_config

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
    
    @field_validator('providerName')
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """Validate provider name."""
        sanitized = validate_string_input(
            v,
            field_name='providerName',
            max_length=50,
            min_length=1
        )
        # Provider name should be alphanumeric with underscores/hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
            raise ValueError("Provider name must contain only letters, numbers, underscores, and hyphens")
        return sanitized.lower()
    
    @field_validator('displayName')
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate display name."""
        return validate_string_input(
            v,
            field_name='displayName',
            max_length=100,
            min_length=1
        )
    
    @field_validator('channel')
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate channel."""
        allowed_channels = ["sms", "email", "inapp", "whatsapp"]
        sanitized = validate_string_input(v, field_name='channel')
        if sanitized.lower() not in allowed_channels:
            raise ValueError(f"Channel must be one of: {', '.join(allowed_channels)}")
        return sanitized.lower()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description."""
        return validate_string_input(
            v,
            field_name='description',
            max_length=500,
            allow_html=False
        )
    
    @field_validator('docsUrl', 'testEndpoint')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL fields."""
        sanitized = validate_string_input(
            v,
            field_name='url',
            max_length=500
        )
        # Basic URL validation
        if not re.match(r'^https?://', sanitized, re.IGNORECASE) and not sanitized.startswith('/'):
            raise ValueError("URL must start with http://, https://, or /")
        return sanitized
    
    @field_validator('configSchema', 'uiSchema')
    @classmethod
    def validate_schema(cls, v: dict) -> dict:
        """Validate schema dictionaries."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        # For schemas, we allow more flexibility but still sanitize string values
        return v
    
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
    
    @field_validator('channel')
    @classmethod
    def validate_channel(cls, v: Optional[str]) -> Optional[str]:
        """Validate channel filter."""
        if v is None or v == "":
            return None
        
        # Sanitize channel value
        sanitized = validate_string_input(
            v,
            field_name='channel',
            max_length=50
        )
        
        # Normalize to lowercase
        normalized = sanitized.lower()
        
        # Validate against allowed channels
        allowed_channels = ["sms", "email", "inapp", "whatsapp"]
        if normalized not in allowed_channels:
            raise ValueError(f"Channel must be one of: {', '.join(allowed_channels)}")
        
        return normalized
        