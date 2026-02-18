"""Email template request, response, and filter DTOs."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional
from uuid import uuid4, UUID
from datetime import datetime
import re

from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.shared.validators.input_validators import validateStringInput


class EmailTemplateRequestDTO(BaseModel):
    """Request DTO for creating/updating email templates."""

    templateName: str = Field(alias="templateName")
    tenantId: UUID = Field(alias="tenantId")
    serviceName: str = Field(alias="serviceName")
    subject: str = Field(description="Email subject line with optional placeholders")
    version: int
    isActive: bool = Field(alias="isActive")
    bodyType: str = Field(default="html", alias="bodyType", description="Body type: 'html' or 'text'")
    body: Dict[str, str] = Field(description="Email body content per language")
    fileUrls: Optional[str] = Field(default=None, alias="fileUrls", description="Optional attachment URLs")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "templateName": "WelcomeEmail",
                "tenantId": "123e4567-e89b-12d3-a456-426614174000",
                "serviceName": "UserOnboarding",
                "subject": "Welcome to {companyName}, {userName}!",
                "version": 1,
                "isActive": True,
                "bodyType": "html",
                "body": {
                    "en": "<html><body><h1>Welcome {userName}!</h1><p>Thank you for joining {companyName}.</p></body></html>",
                    "es": "<html><body><h1>¡Bienvenido {userName}!</h1><p>Gracias por unirse a {companyName}.</p></body></html>",
                },
                "fileUrls": None,
            }
        },
    )

    @field_validator("templateName")
    @classmethod
    def validateTemplateName(cls, v: str) -> str:
        """Validate template name."""
        sanitized = validateStringInput(v, fieldName="templateName", maxLength=100, minLength=1)
        # Template name should be alphanumeric with underscores/hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", sanitized):
            raise ValueError(
                "Template name must contain only letters, numbers, underscores, and hyphens"
            )
        return sanitized

    @field_validator("serviceName")
    @classmethod
    def validateServiceName(cls, v: str) -> str:
        """Validate service name."""
        return validateStringInput(v, fieldName="serviceName", maxLength=100, minLength=1)

    @field_validator("subject")
    @classmethod
    def validateSubject(cls, v: str) -> str:
        """Validate email subject."""
        return validateStringInput(v, fieldName="subject", maxLength=255, minLength=1)

    @field_validator("version")
    @classmethod
    def validateVersion(cls, v: int) -> int:
        """Validate version number."""
        if v < 1:
            raise ValueError("Version must be at least 1")
        if v > 9999:
            raise ValueError("Version exceeds maximum allowed value")
        return v

    @field_validator("bodyType")
    @classmethod
    def validateBodyType(cls, v: str) -> str:
        """Validate body type."""
        normalized = v.lower()
        if normalized not in ["html", "text"]:
            raise ValueError("Body type must be 'html' or 'text'")
        return normalized

    @field_validator("body")
    @classmethod
    def validateBody(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate template body for each language."""
        if not v:
            raise ValueError("Template body cannot be empty")

        sanitized_content = {}
        for lang, template_text in v.items():
            # Validate language code (2-5 characters, alphanumeric)
            if not re.match(r"^[a-zA-Z0-9-]{2,5}$", lang):
                raise ValueError(f"Invalid language code: {lang}")

            # Validate template text
            if not isinstance(template_text, str) or not template_text.strip():
                raise ValueError(f"Template text for language '{lang}' cannot be empty")

            # For email template bodies:
            # - SQL injection check is NOT needed because this content is stored as JSONB
            #   and never concatenated into SQL queries
            # - HTML comments (<!-- -->) legitimately contain "--" which triggers false positives
            # - Just do length validation and basic sanitization
            
            if len(template_text) > 50000:
                raise ValueError(f"body.{lang} exceeds maximum length of 50000 characters")
            
            # Strip whitespace only, preserve HTML content as-is
            sanitized_content[lang] = template_text.strip()

        return sanitized_content

    def toEntity(self) -> EmailTemplate:
        """Convert DTO to domain entity."""
        return EmailTemplate(
            id=uuid4(),
            tenantId=self.tenantId,
            templateName=self.templateName,
            serviceName=self.serviceName,
            subject=self.subject,
            isActive=self.isActive,
            version=self.version,
            bodyType=self.bodyType,
            body=self.body,
            fileUrls=self.fileUrls,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
        )


class EmailTemplateResponseDTO(BaseModel):
    """Response DTO for email templates."""

    id: UUID
    tenantId: UUID = Field(alias="tenantId")
    templateName: str = Field(alias="templateName")
    serviceName: str = Field(alias="serviceName")
    subject: str
    version: int
    isActive: bool = Field(alias="isActive")
    bodyType: str = Field(alias="bodyType")
    body: Dict[str, str]
    fileUrls: Optional[str] = Field(default=None, alias="fileUrls")
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=False
    )

    @classmethod
    def fromEntityWithRelations(cls, template: EmailTemplate):
        """Create DTO from entity with related data."""
        return cls(
            id=template.id,
            tenantId=template.tenantId,
            templateName=template.templateName,
            serviceName=template.serviceName,
            subject=template.subject,
            version=template.version,
            isActive=template.isActive,
            bodyType=template.bodyType,
            body=template.body,
            fileUrls=template.fileUrls,
            createdAt=template.createdAt,
            updatedAt=template.updatedAt,
        )


class EmailTemplateFilterDTO(PaginatedRequestDTO):
    """Filter DTO for email template queries with custom filters."""

    isActive: Optional[bool] = Field(None, description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")

    @field_validator("tenantId")
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        # UUID validation is handled by Pydantic automatically
        return v
