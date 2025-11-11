from pydantic import BaseModel,ConfigDict,Field
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
class SMSTemplateRequestDTO(BaseModel):
    templateName: str = Field(alias="template_name")
    tenantId: UUID = Field(alias="tenant_id")
    serviceName: str = Field(alias="service_name")
    version: int
    isActive: bool = Field(alias="is_active")
    content: Dict[str, str]
    model_config=ConfigDict(from_attributes=True, populate_by_name=True, json_schema_extra={
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
    
    def toEntity(self) -> SmsTemplate:
        """Convert DTO to domain entity."""
        return SmsTemplate(  # ✅ Create SmsTemplate, not SMSTemplateRequestDTO
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
        
class SMSTemplateResponseDTO(BaseModel):
    id: UUID
    tenantId: UUID = Field(alias="tenant_id")
    templateName: str = Field(alias="template_name")
    serviceName: str = Field(alias="service_name")
    version: int
    isActive: bool = Field(alias="is_active")
    content: Dict[str, str]
    createdAt: datetime = Field(alias="created_at")
    updatedAt: datetime = Field(alias="updated_at")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    @classmethod
    def fromEntityWithRelations(cls, template: SmsTemplate):
        """Create DTO from entity with related data."""
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
class SMSTemplateFilters(BaseModel):
    tenantId:UUID = Field(alias="tenant_id")
    templateName:str = Field(alias="template_name")
    serviceName: str = Field(alias="service_name")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "template_name": "WelcomeTemplate",
                "service_name": "UserOnboarding"
            }
        }

