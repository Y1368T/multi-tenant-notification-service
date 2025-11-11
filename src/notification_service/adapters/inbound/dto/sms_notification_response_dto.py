from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class SMSNotificationResponseDTO(BaseModel):
    """Response DTO for SMS notifications with enriched data."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    # SMS Notification fields
    id: UUID
    recipientNumber: str = Field(alias="recipient_number")
    messageContent: Dict[str, Any] = Field(alias="message_content")
    status: str
    idempotencyKey: Optional[str] = Field(default=None, alias="idempotency_key")
    templateId: UUID = Field(alias="template_id")
    createdAt: datetime = Field(alias="created_at")
    updatedAt: datetime = Field(alias="updated_at")
    
    # Enriched fields from related entities
    templateName: str = Field(alias="template_name")
    tenantName: str = Field(alias="tenant_name")
    tenantPrefix: str = Field(alias="tenant_prefix")
    
    @classmethod
    def fromEntityWithRelations(cls, notification):
        """Create DTO from entity with related data."""
        # Extract template and tenant data safely
        templateName = "Unknown"
        tenantName = "Unknown"
        tenantPrefix = "Unknown"
        
        if notification.template:
            templateName = notification.template.templateName or "Unknown"
            if notification.template.tenant:
                tenantName = notification.template.tenant.name or "Unknown"
                tenantPrefix = notification.template.tenant.prefix or "Unknown"
        
        return cls(
            id=notification.id,
            recipientNumber=notification.recipientNumber,
            messageContent=notification.messageContent,
            status=notification.status,
            idempotencyKey=notification.idempotencyKey,
            templateId=notification.templateId,
            createdAt=notification.createdAt,
            updatedAt=notification.updatedAt,
            templateName=templateName,
            tenantName=tenantName,
            tenantPrefix=tenantPrefix
        )

