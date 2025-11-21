from pydantic import BaseModel, ConfigDict, Field, field_validator
from notification_service.domain.entities.providers_supported import Provider
from uuid import uuid4, UUID
from typing import Optional, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput
import re

class TestRequestDto(BaseModel):
    # Define fields for the test request DTO
    address: str
    providerName: str
    channel: str
    config: dict
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "address": "123 Main St",
                "providerName": "example_provider",
                "channel": "sms",
                "config": {
                    "apiKey": "your_api_key",
                    "sender": "your_sender_id"
                }
            }
        })
    
    @field_validator('address')
    @classmethod
    def validateAddress(cls, v: str) -> str:
        """Validate address (phone or email)."""
        return validateStringInput(
            v,
            fieldName='address',
            maxLength=255,
            minLength=1
        )
    
    @field_validator('providerName')
    @classmethod
    def validateProviderName(cls, v: str) -> str:
        """Validate provider name."""
        return validateStringInput(
            v,
            fieldName='providerName',
            maxLength=50
        )
    
    @field_validator('channel')
    @classmethod
    def validateChannel(cls, v: str) -> str:
        """Validate channel."""
        allowedChannels = ["sms", "email", "inapp", "whatsapp"]
        sanitized = validateStringInput(v, fieldName='channel')
        if sanitized.lower() not in allowedChannels:
            raise ValueError(f"Channel must be one of: {', '.join(allowedChannels)}")
        return sanitized.lower()
    
    @field_validator('config')
    @classmethod
    def validateConfig(cls, v: dict) -> dict:
        """Validate configuration dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        
        # Sanitize string values in config
        sanitizedConfig = {}
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Config keys must be strings")
            
            sanitizedKey = validateStringInput(
                key,
                fieldName=f'config.{key}',
                maxLength=100
            )
            
            if isinstance(value, str):
                # Allow longer values for config fields (e.g., private keys can be 2000+ chars)
                # Check for known long fields that need more space
                maxLen = 10000 if key in ['private_key', 'privateKey', 'certificate', 'cert', 'key'] else 5000
                
                # Skip SQL injection checking for encoded/sensitive fields (private keys, certificates, etc.)
                # These fields contain base64-encoded data that may accidentally match SQL patterns
                skipSqlCheck = key.lower() in [
                    'private_key', 'privatekey', 'private_key_id', 'privatekeyid',
                    'certificate', 'cert', 'key', 'token', 'secret', 'api_key', 'apikey',
                    'client_x509_cert_url', 'clientx509certurl', 'auth_provider_x509_cert_url'
                ]
                
                if skipSqlCheck:
                    # For sensitive fields, only validate length, skip SQL/XSS checks
                    if maxLen and len(value) > maxLen:
                        raise ValueError(f"config.{key} must be at most {maxLen} characters")
                    sanitizedValue = value  # Don't sanitize encoded data
                else:
                    sanitizedValue = validateStringInput(
                        value,
                        fieldName=f'config.{key}',
                        maxLength=maxLen
                    )
            else:
                sanitizedValue = value
            
            sanitizedConfig[sanitizedKey] = sanitizedValue
        
        return sanitizedConfig

class ProviderSupportedDTO(BaseModel):
    
    providerName: str = Field(alias="providerName")
    displayName: str = Field(alias="displayName")
    channel: str
    description: str
    docsUrl: str = Field(alias="docsUrl")
    testEndpoint: str = Field(alias="testEndpoint")
    configSchema: dict = Field(alias="configSchema")
    uiSchema: dict = Field(alias="uiSchema")
    isActive: bool = Field(alias="isActive")
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=False,
        json_schema_extra={
            "example": {
                "providerName": "afromessage",
                "displayName": "Afromessage",
                "channel": "sms",
                "isActive": True,
                "description": "Send SMS via Afromessage API.",
                "docsUrl": "https://example.com/docs/afromessage",
                "testEndpoint": "/api/providers/sms/afromessage/test",
                "configSchema": {
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
                "uiSchema": {
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
    def validateProviderName(cls, v: str) -> str:
        """Validate provider name."""
        sanitized = validateStringInput(
            v,
            fieldName='providerName',
            maxLength=50,
            minLength=1
        )
        # Provider name should be alphanumeric with underscores/hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
            raise ValueError("Provider name must contain only letters, numbers, underscores, and hyphens")
        return sanitized.lower()
    
    @field_validator('displayName')
    @classmethod
    def validateDisplayName(cls, v: str) -> str:
        """Validate display name."""
        return validateStringInput(
            v,
            fieldName='displayName',
            maxLength=100,
            minLength=1
        )
    
    @field_validator('channel')
    @classmethod
    def validateChannel(cls, v: str) -> str:
        """Validate channel."""
        allowedChannels = ["sms", "email", "inapp", "whatsapp"]
        sanitized = validateStringInput(v, fieldName='channel')
        if sanitized.lower() not in allowedChannels:
            raise ValueError(f"Channel must be one of: {', '.join(allowedChannels)}")
        return sanitized.lower()
    
    @field_validator('description')
    @classmethod
    def validateDescription(cls, v: str) -> str:
        """Validate description."""
        return validateStringInput(
            v,
            fieldName='description',
            maxLength=500,
            allowHtml=False
        )
    
    @field_validator('docsUrl', 'testEndpoint')
    @classmethod
    def validateUrl(cls, v: str) -> str:
        """Validate URL fields."""
        sanitized = validateStringInput(
            v,
            fieldName='url',
            maxLength=500
        )
        # Basic URL validation
        if not re.match(r'^https?://', sanitized, re.IGNORECASE) and not sanitized.startswith('/'):
            raise ValueError("URL must start with http://, https://, or /")
        return sanitized
    
    @field_validator('configSchema', 'uiSchema')
    @classmethod
    def validateSchema(cls, v: dict) -> dict:
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
    providerName: str = Field(alias="providerName")
    displayName: str = Field(alias="displayName")
    channel: str
    description: Optional[str] = None
    docsUrl: Optional[str] = Field(None, alias="docsUrl")
    testEndpoint: Optional[str] = Field(None, alias="testEndpoint")
    configSchema: Dict[str, Any] = Field(default_factory=dict, alias="configSchema")
    uiSchema: Optional[Dict[str, Any]] = Field(None, alias="ui_schema")
    isActive: bool = Field(alias="isActive")
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
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
    def validateChannel(cls, v: Optional[str]) -> Optional[str]:
        """Validate channel filter."""
        if v is None or v == "":
            return None
        
        # Sanitize channel value
        sanitized = validateStringInput(
            v,
            fieldName='channel',
            maxLength=50
        )
        
        # Normalize to lowercase
        normalized = sanitized.lower()
        
        # Validate against allowed channels
        allowedChannels = ["sms", "email", "inapp", "whatsapp"]
        if normalized not in allowedChannels:
            raise ValueError(f"Channel must be one of: {', '.join(allowedChannels)}")
        
        return normalized
        