from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from uuid import UUID
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input
import re

class InAppTemplateRequestDTO(BaseModel):
    templateName: str = Field(alias="templateName")
    tenantId: UUID = Field(alias="tenantId")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    body: Dict[str, Dict[str, Any]]
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional FCM data payload (applies to all languages)")
    android: Optional[Dict[str, Any]] = Field(default=None, description="Optional Android-specific config (applies to all languages)")
    apns: Optional[Dict[str, Any]] = Field(default=None, description="Optional iOS/APNS-specific config (applies to all languages)")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "templateName": "WelcomeTemplate",
                "tenantId": "123e4567-e89b-12d3-a456-426614174000",
                "serviceName": "UserOnboarding",
                "version": 1,
                "isActive": True,
                "body": 
                { 
                    "en":{
                        "title": "Welcome {userName}!",
                        "message": "Hello {userName}, welcome to our service!",
                        "actionUrl": "https://example.com/welcome"
                    },
                    "amh": {
                        "title": "Welcome {userName}!",
                        "message": "Hello {userName}, welcome to our service!",
                        "actionUrl": "https://example.com/welcome"
                    },
                    "ar": {
                        "title": "Welcome {userName}!",
                        "message": "Hello {userName}, welcome to our service!",
                        "actionUrl": "https://example.com/welcome"
                    }
                },
                 "data": {
                    "userId": "{userId}",
                    "action": "open_profile"
                },
                "android": {
                    "priority": "high",
                    "notification": {
                        "sound": "default",
                        "channel_id": "important_channel"
                    }
                },
                "apns": {
                    "headers": {
                        "apns-priority": "10"
                    },
                    "payload": {
                        "aps": {
                            "sound": "default",
                            "badge": 1
                        }
                    }
                }

            }
        })
    
    @field_validator('templateName')
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        """Validate template name."""
        sanitized = validate_string_input(
            v,
            field_name='templateName',
            max_length=100,
            min_length=1
        )
        # Template name should be alphanumeric with underscores/hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
            raise ValueError("Template name must contain only letters, numbers, underscores, and hyphens")
        return sanitized
    
    @field_validator('serviceName')
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate service name."""
        return validate_string_input(
            v,
            field_name='serviceName',
            max_length=100,
            min_length=1
        )
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v: int) -> int:
        """Validate version number."""
        if v < 1:
            raise ValueError("Version must be at least 1")
        if v > 9999:
            raise ValueError("Version exceeds maximum allowed value")
        return v
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate template body for each language and field."""
        if not v:
            raise ValueError("Template body cannot be empty")
        
        sanitized_body = {}
        for lang_code, lang_body in v.items():
            # Validate language code
            if not isinstance(lang_code, str):
                raise ValueError(f"Language code '{lang_code}' must be a string")
            
            # Validate language code format (2-5 characters, alphanumeric with hyphens)
            if not re.match(r'^[a-zA-Z0-9-]{2,5}$', lang_code):
                raise ValueError(f"Invalid language code: {lang_code}")
            
            # Validate that lang_body is a dictionary
            if not isinstance(lang_body, dict):
                raise ValueError(f"Body value for language '{lang_code}' must be a dictionary")
            
            if not lang_body:
                raise ValueError(f"Body dictionary for language '{lang_code}' cannot be empty")
            
            # Validate and sanitize each field in the language body
            sanitized_lang_body = {}
            for field_key, field_value in lang_body.items():
                # Validate field key
                if not isinstance(field_key, str):
                    raise ValueError(f"Field key '{field_key}' in language '{lang_code}' must be a string")
                
                # All fields in language body (title, message, actionUrl, etc.) should be strings
                # Note: data, android, apns are now top-level optional fields, not in language body
                if field_value is None:
                    sanitized_lang_body[field_key] = None
                elif not isinstance(field_value, str):
                    raise ValueError(f"Field '{field_key}' value for language '{lang_code}' must be a string")
                else:
                    if not field_value.strip():
                        raise ValueError(f"Field '{field_key}' value for language '{lang_code}' cannot be empty")
                    
                    # Sanitize field value (allow placeholders like {userName})
                    sanitized = validate_string_input(
                        field_value,
                        field_name=f'body.{lang_code}.{field_key}',
                        max_length=2000,
                        allow_html=True  # Allow HTML in in-app templates
                    )
                    
                    sanitized_lang_body[field_key] = sanitized
            
            sanitized_body[lang_code] = sanitized_lang_body
        
        return sanitized_body
    @field_validator('data', 'android', 'apns')
    @classmethod
    def validate_platform_config(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate platform-specific configuration (optional)."""
        if v is None:
            return None
        
        if not isinstance(v, dict):
            raise ValueError("Platform config must be a dictionary or null")
        
        # Recursively validate nested dictionary structures
        return cls._validate_nested_dict(v, 'platform_config')
    
    @classmethod
    def _validate_nested_dict(cls, value: Any, field_path: str) -> Any:
        """Recursively validate nested dictionary structures."""
        if isinstance(value, dict):
            return {k: cls._validate_nested_dict(v, f'{field_path}.{k}') for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._validate_nested_dict(item, f'{field_path}[{i}]') for i, item in enumerate(value)]
        elif isinstance(value, str):
            # Validate string values in nested structures
            return validate_string_input(
                value,
                field_name=field_path,
                max_length=5000,  # Longer limit for nested values
                allow_html=False
            )
        elif isinstance(value, (int, float, bool)):
            # Allow numbers and booleans in nested structures
            return value
        elif value is None:
            return None
        else:
            raise ValueError(f"Invalid value type in {field_path}: {type(value).__name__}")
    
    def toEntity(self) -> InAppTemplate:
        """Convert DTO to domain entity."""
        entity_body=self.body.copy()
        if self.data is not None:
            entity_body["data"] = self.data
        if self.android is not None:
            entity_body["android"] = self.android
        if self.apns is not None:
            entity_body["apns"] = self.apns
        return InAppTemplate(
            id=uuid4(),
            tenantId=self.tenantId,
            templateName=self.templateName,
            serviceName=self.serviceName,
            isActive=self.isActive,
            version=self.version,
            body=entity_body,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

class InAppTemplateResponseDTO(BaseModel):
    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    templateName: str = Field(alias="templateName")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    body: Dict[str, Dict[str, Any]]
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional FCM data payload (applies to all languages)")
    android: Optional[Dict[str, Any]] = Field(default=None, description="Optional Android-specific config (applies to all languages)")
    apns: Optional[Dict[str, Any]] = Field(default=None, description="Optional iOS/APNS-specific config (applies to all languages)")
    
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, template: InAppTemplate):
        """Create DTO from entity with related data."""
        # Extract platform configs from body and exclude them from body
        data = template.body.get('data')
        android = template.body.get('android')
        apns = template.body.get('apns')
        # Filter out platform configs and internal keys (starting with _) from body
        body = {
            k: v for k, v in template.body.items() 
            if k not in ['data', 'android', 'apns'] and not k.startswith('_')
        }
        return cls(
            id=template.id,
            tenantId=template.tenantId,
            templateName=template.templateName,
            serviceName=template.serviceName,
            version=template.version,
            isActive=template.isActive,
            body=body,
            data=data,
            android=android,
            apns=apns,
            createdAt=template.createdAt,
            updatedAt=template.updatedAt
        )

class InAppTemplateFilterDTO(PaginatedRequestDTO):
    """Filter DTO for in-app template queries with custom filters."""
    isActive: Optional[bool] = Field(None, description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    
    @field_validator('tenantId')
    @classmethod
    def validate_tenant_id(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        # UUID validation is handled by Pydantic automatically
        return v

