from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class InAppNotificationResponseDTO(BaseModel):
    """Response DTO for in-app notifications with enriched data."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    # In-App Notification fields
    id: UUID
    recipientUserId: str = Field(alias="recipientUserId")
    messageContent: str = Field(alias="messageContent")
    status: str
    idempotencyKey: Optional[str] = Field(default=None, alias="idempotencyKey")
    templateId: Optional[UUID] = Field(default=None, alias="templateId")
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    # Enriched fields from related entities
    templateName: str = Field(alias="templateName")
    tenantName: str = Field(alias="tenantName")
    tenantPrefix: str = Field(alias="tenantPrefix")
    
    @classmethod
    def fromEntityWithRelations(cls, notification):
        """Create DTO from entity with related data."""
        # Extract template and tenant data safely
        templateName = "Unknown"
        tenantName = "Unknown"
        tenantPrefix = "Unknown"
        
        # First check if templateName is directly available on the notification entity
        if hasattr(notification, 'templateName') and notification.templateName:
            templateName = notification.templateName
        elif notification.template:
            templateName = notification.template.templateName or "Unknown"
            # Check if tenant is loaded on the template
            if notification.template.tenant:
                tenantName = notification.template.tenant.name or "Unknown"
                tenantPrefix = notification.template.tenant.prefix or "Unknown"
        
        return cls(
            id=notification.id,
            recipientUserId=notification.recipientUserId,
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

