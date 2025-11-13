from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validate_string_input
import re
class SMSTemplateRequestDTO(BaseModel):
    templateName: str = Field(alias="templateName")
    tenantId: UUID = Field(alias="tenantId")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    content: Dict[str, str]
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
                "content": {
                    "en": "Hello {userName}, welcome to our service!",
                    "es": "Hola {userName}, ¡bienvenido a nuestro servicio!"
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
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate template content for each language."""
        if not v:
            raise ValueError("Template content cannot be empty")
        
        sanitized_content = {}
        for lang, template_text in v.items():
            # Validate language code (2-5 characters, alphanumeric)
            if not re.match(r'^[a-zA-Z0-9-]{2,5}$', lang):
                raise ValueError(f"Invalid language code: {lang}")
            
            # Validate template text
            if not isinstance(template_text, str) or not template_text.strip():
                raise ValueError(f"Template text for language '{lang}' cannot be empty")
            
            # Sanitize template text (allow placeholders like {userName})
            sanitized = validate_string_input(
                template_text,
                field_name=f'content.{lang}',
                max_length=1000,
                allow_html=False  # No HTML in SMS templates
            )
            
            sanitized_content[lang] = sanitized
        
        return sanitized_content
    
    def toEntity(self) -> SmsTemplate:
        """Convert DTO to domain entity."""
        return SmsTemplate(  # ✅ Create SmsTemplate, not SMSTemplateRequestDTO
            id=uuid4(),
            tenantId=self.tenantId,
            templateName=self.templateName,
            serviceName=self.serviceName,
            isActive=self.isActive,
            version=self.version,
            content=self.content,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
class SMSTemplateResponseDTO(BaseModel):
    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    templateName: str = Field(alias="templateName")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    content: Dict[str, str]
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, template: SmsTemplate):
        """Create DTO from entity with related data."""
        return cls(
            id=template.id,
            tenantId=template.tenantId,
            templateName=template.templateName,
            serviceName=template.serviceName,
            version=template.version,
            isActive=template.isActive,
            content=template.content,
            createdAt=template.createdAt,
            updatedAt=template.updatedAt
        )
class SMSTemplateFilterDTO(PaginatedRequestDTO):
    """Filter DTO for SMS template queries with custom filters."""
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

