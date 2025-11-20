from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from notification_service.domain.entities.sms.sms_notification import SMSNotification


class SMSNotificationResponseDTO(BaseModel):
    """Response DTO for SMS notifications with enriched data."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    # SMS Notification fields
    id: UUID
    recipientNumber: str = Field(alias="recipientNumber")
    messageContent: Dict[str, Any] = Field(alias="messageContent")
    status: str
    idempotencyKey: Optional[str] = Field(default=None, alias="idempotencyKey")
    templateId: Optional[UUID] = Field(default=None, alias="templateId")
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    # Enriched fields from related entities
    templateName: Optional[str] = Field(default=None, alias="templateName")
    serviceName: Optional[str] = Field(default=None, alias="serviceName")
    tenantId: Optional[UUID] = Field(default=None, alias="tenantId")
    tenantName: Optional[str] = Field(default=None, alias="tenantName")
    tenantPrefix: Optional[str] = Field(default=None, alias="tenantPrefix")
    
    @classmethod
    def fromEntityWithRelations(cls, notification: SMSNotification):
        """Create DTO from entity with related data."""
        # Extract template and tenant data safely
        template_name = None
        service_name = None
        tenant_id = None
        tenant_name = None
        tenant_prefix = None
        
        # First check if templateName is directly available on the notification entity
        if hasattr(notification, 'templateName') and notification.templateName:
            template_name = notification.templateName
        elif hasattr(notification, 'template') and notification.template:
            template_name = notification.template.templateName or None
            service_name = notification.template.serviceName or None
            # Check if tenant is loaded on the template
            if hasattr(notification.template, 'tenant') and notification.template.tenant:
                tenant_id = notification.template.tenant.id
                tenant_name = notification.template.tenant.name or None
                tenant_prefix = notification.template.tenant.prefix or None
        
        return cls(
            id=notification.id,
            recipientNumber=notification.recipientNumber,
            messageContent=notification.messageContent,
            status=notification.status,
            idempotencyKey=notification.idempotencyKey,
            templateId=notification.templateId,
            createdAt=notification.createdAt,
            updatedAt=notification.updatedAt,
            templateName=template_name,
            serviceName=service_name,
            tenantId=tenant_id,
            tenantName=tenant_name,
            tenantPrefix=tenant_prefix
        )
