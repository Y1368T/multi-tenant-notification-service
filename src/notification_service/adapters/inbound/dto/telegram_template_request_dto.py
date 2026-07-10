from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from uuid import UUID
import re

from notification_service.domain.entities.telegram.telegram_template import TelegramTemplate
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.shared.validators.input_validators import validateStringInput


class TelegramTemplateRequestDTO(BaseModel):
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
                    "en": "Hello {userName}, welcome to our Telegram channel!",
                    "es": "Hola {userName}, ¡bienvenido a nuestro canal de Telegram!"
                }
            }
        })
    
    @field_validator('templateName')
    @classmethod
    def validateTemplateName(cls, v: str) -> str:
        sanitized = validateStringInput(
            v,
            fieldName='templateName',
            maxLength=100,
            minLength=1
        )
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
            raise ValueError("Template name must contain only letters, numbers, underscores, and hyphens")
        return sanitized
    
    @field_validator('serviceName')
    @classmethod
    def validateServiceName(cls, v: str) -> str:
        return validateStringInput(
            v,
            fieldName='serviceName',
            maxLength=100,
            minLength=1
        )
    
    @field_validator('version')
    @classmethod
    def validateVersion(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Version must be at least 1")
        if v > 9999:
            raise ValueError("Version exceeds maximum allowed value")
        return v
    
    @field_validator('content')
    @classmethod
    def validateContent(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v:
            raise ValueError("Template content cannot be empty")
        
        sanitized_content = {}
        for lang, template_text in v.items():
            if not re.match(r'^[a-zA-Z0-9-]{2,5}$', lang):
                raise ValueError(f"Invalid language code: {lang}")
            
            if not isinstance(template_text, str) or not template_text.strip():
                raise ValueError(f"Template text for language '{lang}' cannot be empty")
            
            sanitized = validateStringInput(
                template_text,
                fieldName=f'content.{lang}',
                maxLength=4000,  # Telegram supports longer messages than SMS
                allowHtml=True   # Telegram supports HTML formatting
            )
            sanitized_content[lang] = sanitized
        
        return sanitized_content
    
    def toEntity(self) -> TelegramTemplate:
        return TelegramTemplate(
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


class TelegramTemplateResponseDTO(BaseModel):
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
    def fromEntityWithRelations(cls, template: TelegramTemplate):
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


class TelegramTemplateFilterDTO(PaginatedRequestDTO):
    isActive: Optional[bool] = Field(None, description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    
    @field_validator('tenantId')
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        if v is None:
            return None
        return v
