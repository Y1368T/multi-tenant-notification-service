from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from notification_service.domain.entities.in_app.in_app_outbox import InAppOutbox

class InAppOutboxResponseDTO(BaseModel):
    id: UUID
    templateId: Optional[UUID] = Field(None, alias="template_id")
    recipientUserId: str = Field(alias="recipient_user_id")
    messageContent: Dict[str, Dict[str, str]] = Field(alias="message_content")
    idempotencyKey: Optional[str] = Field(None, alias="idempotency_key")
    retryCount: int = Field(alias="retry_count")
    lastRetryAt: Optional[datetime] = Field(None, alias="last_retry_at")
    lastErrorMessage: Optional[str] = Field(None, alias="last_error_message")
    nextRetryAt: Optional[datetime] = Field(None, alias="next_retry_at")
    providerAttempted: Optional[str] = Field(None, alias="provider_attempted")
    isSent: bool = Field(alias="is_sent")
    sentAt: Optional[datetime] = Field(None, alias="sent_at")
    status: str
    createdAt: datetime = Field(alias="created_at")
    updatedAt: datetime = Field(alias="updated_at")
    
    # Enriched fields from relationships
    templateName: Optional[str] = Field(None, alias="template_name")
    serviceName: Optional[str] = Field(None, alias="service_name")
    tenantId: Optional[UUID] = Field(None, alias="tenant_id")
    tenantName: Optional[str] = Field(None, alias="tenant_name")
    tenantPrefix: Optional[str] = Field(None, alias="tenant_prefix")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, outbox: InAppOutbox):
        """Create DTO from entity with related data."""
        template_name = None
        service_name = None
        tenant_id = None
        tenant_name = None
        tenant_prefix = None
        
        # Extract from template if available
        if hasattr(outbox, 'template') and outbox.template:
            template_name = outbox.template.templateName
            service_name = outbox.template.serviceName
            if hasattr(outbox.template, 'tenant') and outbox.template.tenant:
                tenant_id = outbox.template.tenant.id
                tenant_name = outbox.template.tenant.name
                tenant_prefix = outbox.template.tenant.prefix
        
        return cls(
            id=outbox.id,
            templateId=outbox.templateId,
            recipientUserId=outbox.recipientUserId,
            messageContent=outbox.messageContent,
            idempotencyKey=outbox.idempotencyKey,
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
            tenantPrefix=tenant_prefix
        )

