from pydantic import BaseModel,ConfigDict
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
class SMSTemplateRequestDTO(BaseModel):
    template_name: str
    tenant_id: UUID
    service_name: str
    version: int
    is_active: bool
    content: Dict[str, str]
    model_config=ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "template_name": "WelcomeTemplate",
            "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
            "service_name": "UserOnboarding",
            "version": 1,
            "is_active": True,
            "content": {
                "en": "Hello {user_name}, welcome to our service!",
                "es": "Hola {user_name}, ¡bienvenido a nuestro servicio!"
            }
        }
    })
    
    def to_entity(self) -> SmsTemplate:
        """Convert DTO to domain entity."""
        return SmsTemplate(  # ✅ Create SmsTemplate, not SMSTemplateRequestDTO
            id=uuid4(),
            tenant_id=self.tenant_id,
            template_name=self.template_name,
            service_name=self.service_name,
            is_active=self.is_active,
            version=self.version,
            content=self.content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
class SMSTemplateFilters(BaseModel):
    tenant_id:UUID
    template_name:str
    service_name: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "template_name": "WelcomeTemplate",
                "service_name": "UserOnboarding"
            }
        }

