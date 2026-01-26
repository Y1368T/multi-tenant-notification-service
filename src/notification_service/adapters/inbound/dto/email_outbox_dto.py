"""Email outbox DTOs."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID

from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.shared.validators.input_validators import validateStringInput


class EmailOutboxResponseDTO(BaseModel):
    """Response DTO for Email outbox with enriched data."""

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=False
    )

    # Email Outbox fields
    id: UUID
    recipientEmail: str = Field(alias="recipientEmail")
    messageContent: Union[Dict[str, Any], str] = Field(alias="messageContent")
    idempotencyKey: str = Field(alias="idempotencyKey")
    templateId: Optional[UUID] = Field(default=None, alias="templateId")
    retryCount: int = Field(alias="retryCount")
    lastRetryAt: Optional[datetime] = Field(default=None, alias="lastRetryAt")
    lastErrorMessage: Optional[str] = Field(default=None, alias="lastErrorMessage")
    nextRetryAt: Optional[datetime] = Field(default=None, alias="nextRetryAt")
    providerAttempted: Optional[str] = Field(default=None, alias="providerAttempted")
    isSent: bool = Field(alias="isSent")
    sentAt: Optional[datetime] = Field(default=None, alias="sentAt")
    status: str
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")

    # Enriched fields from related entities
    templateName: Optional[str] = Field(default=None, alias="templateName")
    serviceName: Optional[str] = Field(default=None, alias="serviceName")
    tenantId: Optional[UUID] = Field(default=None, alias="tenantId")
    tenantName: Optional[str] = Field(default=None, alias="tenantName")

    @classmethod
    def fromEntityWithRelations(cls, outbox: EmailOutbox):
        """Create DTO from entity with related data."""
        template_name = None
        service_name = None
        tenant_id = None
        tenant_name = None

        if hasattr(outbox, "template") and outbox.template:
            template_name = outbox.template.templateName or None
            service_name = outbox.template.serviceName or None
            if hasattr(outbox.template, "tenant") and outbox.template.tenant:
                tenant_id = outbox.template.tenant.id
                tenant_name = outbox.template.tenant.name or None

        return cls(
            id=outbox.id,
            recipientEmail=outbox.recipientEmail,
            messageContent=outbox.messageContent,
            idempotencyKey=outbox.idempotencyKey,
            templateId=outbox.templateId,
            retryCount=outbox.retryCount,
            lastRetryAt=outbox.lastRetryAt,
            lastErrorMessage=outbox.lastErrorMessage,
            nextRetryAt=outbox.nextRetryAt,
            providerAttempted=outbox.providerAttempted,
            isSent=outbox.isSent,
            sentAt=outbox.sentAt,
            status=outbox.status,
            createdAt=outbox.createdAt,
            updatedAt=outbox.updatedAt,
            templateName=template_name,
            serviceName=service_name,
            tenantId=tenant_id,
            tenantName=tenant_name,
        )


class EmailOutboxFilterDTO(PaginatedRequestDTO):
    """Filter DTO for Email outbox queries with custom filters."""

    status: Optional[str] = Field(None, description="Filter by outbox status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")
    recipientEmail: Optional[str] = Field(None, description="Filter by recipient email")
    templateName: Optional[str] = Field(None, description="Filter by template name")
    serviceName: Optional[str] = Field(None, description="Filter by service name")

    @field_validator("status")
    @classmethod
    def validateStatus(cls, v: Optional[str]) -> Optional[str]:
        """Validate outbox status filter."""
        if v is None or v == "":
            return None

        sanitized = validateStringInput(v, fieldName="status", maxLength=50)
        normalized = sanitized.lower()

        allowed_statuses = ["pending", "failed", "sent", "retrying"]
        if normalized not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")

        return normalized

    @field_validator("tenantId")
    @classmethod
    def validateTenantId(cls, v: Optional[UUID]) -> Optional[UUID]:
        """Validate tenant ID (UUID format)."""
        if v is None:
            return None
        return v

    @field_validator("recipientEmail")
    @classmethod
    def validateRecipientEmail(cls, v: Optional[str]) -> Optional[str]:
        """Validate recipient email filter."""
        if v is None or v == "":
            return None
        return validateStringInput(v, fieldName="recipientEmail", maxLength=255)
