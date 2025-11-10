from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class SMSNotificationResponseDTO(BaseModel):
    """Response DTO for SMS notifications with enriched data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # SMS Notification fields
    id: UUID
    recipient_number: str
    message_content: Dict[str, Any]
    status: str
    idempotency_key: Optional[str] = None
    template_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Enriched fields from related entities
    template_name: str
    tenant_name: str
    tenant_prefix: str
    
    @classmethod
    def from_entity_with_relations(cls, notification):
        """Create DTO from entity with related data."""
        # Extract template and tenant data safely
        template_name = "Unknown"
        tenant_name = "Unknown"
        tenant_prefix = "Unknown"
        
        if notification.template:
            template_name = notification.template.template_name or "Unknown"
            if notification.template.tenant:
                tenant_name = notification.template.tenant.name or "Unknown"
                tenant_prefix = notification.template.tenant.prefix or "Unknown"
        
        return cls(
            id=notification.id,
            recipient_number=notification.recipient_number,
            message_content=notification.message_content,
            status=notification.status,
            idempotency_key=notification.idempotency_key,
            template_id=notification.template_id,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
            template_name=template_name,
            tenant_name=tenant_name,
            tenant_prefix=tenant_prefix
        )

