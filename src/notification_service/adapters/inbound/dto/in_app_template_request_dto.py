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
    body: Dict[str, Dict[str, str]]
    
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
    def validate_body(cls, v: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
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
                
                # Validate field value
                if not isinstance(field_value, str) or not field_value.strip():
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
    
    def toEntity(self) -> InAppTemplate:
        """Convert DTO to domain entity."""
        return InAppTemplate(
            id=uuid4(),
            tenantId=self.tenantId,
            templateName=self.templateName,
            serviceName=self.serviceName,
            isActive=self.isActive,
            version=self.version,
            body=self.body,
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
    body: Dict[str, Dict[str, str]]
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, template: InAppTemplate):
        """Create DTO from entity with related data."""
        return cls(
            id=template.id,
            tenantId=template.tenantId,
            templateName=template.templateName,
            serviceName=template.serviceName,
            version=template.version,
            isActive=template.isActive,
            body=template.body,
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

