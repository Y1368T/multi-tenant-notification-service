from pydantic import BaseModel,ConfigDict,Field
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO
class SMSTemplateRequestDTO(BaseModel):
    templateName: str = Field(alias="templateName")
    tenantId: UUID = Field(alias="tenantId")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    content: Dict[str, str]
    model_config=ConfigDict(from_attributes=True, populate_by_name=True, json_schema_extra={
        "example": {
            "templateName": "WelcomeTemplate",
            "tenantId": "123e4567-e89b-12d3-a456-426614174000",
            "serviceName": "UserOnboarding",
            "version": 1,
            "isActive": True,
            "content": {
                "en": "Hello {userName}, welcome to our service!",
                "es": "Hola {userName}, ¡bienvenido a nuestro servicio!"
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
    tenantId: UUID = Field(alias="tenantId")
    templateName: str = Field(alias="templateName")
    serviceName: str = Field(alias="serviceName")
    version: int
    isActive: bool = Field(alias="isActive")
    content: Dict[str, str]
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
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
class SMSTemplateFilterDTO(PaginatedRequestDTO):
    """Filter DTO for SMS template queries with custom filters."""
    isActive: Optional[bool] = Field(None,  description="Filter by active status")
    tenantId: Optional[UUID] = Field(None, description="Filter by tenant ID")

