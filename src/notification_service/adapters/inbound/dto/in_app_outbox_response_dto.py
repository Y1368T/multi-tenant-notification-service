from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from notification_service.domain.entities.in_app.in_app_outbox import InAppOutbox

class InAppOutboxResponseDTO(BaseModel):
    id: UUID
    templateId: Optional[UUID] = Field(None, alias="templateId")
    recipientUserId: str = Field(alias="recipientUserId")
    messageContent: Dict[str, Dict[str, str]] = Field(alias="messageContent")
    idempotencyKey: Optional[str] = Field(None, alias="idempotencyKey")
    retryCount: int = Field(alias="retryCount")
    lastRetryAt: Optional[datetime] = Field(None, alias="lastRetryAt")
    lastErrorMessage: Optional[str] = Field(None, alias="lastErrorMessage")
    nextRetryAt: Optional[datetime] = Field(None, alias="nextRetryAt")
    providerAttempted: Optional[str] = Field(None, alias="providerAttempted")
    isSent: bool = Field(alias="isSent")
    sentAt: Optional[datetime] = Field(None, alias="sentAt")
    status: str
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    # Enriched fields from relationships
    templateName: Optional[str] = Field(None, alias="templateName")
    serviceName: Optional[str] = Field(None, alias="serviceName")
    tenantId: Optional[UUID] = Field(None, alias="tenantId")
    tenantName: Optional[str] = Field(None, alias="tenantName")
    tenantPrefix: Optional[str] = Field(None, alias="tenantPrefix")
    
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

