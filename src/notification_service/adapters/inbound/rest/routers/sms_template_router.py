from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
import logging
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantFilterDTO
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.adapters.inbound.dto.sms_template_request_dto import (
    SMSTemplateRequestDTO,
    SMSTemplateResponseDTO,
    SMSTemplateFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)

@api_controller(prefix="/sms-templates", tags=["SMS Templates"])
class SMSTemplateController(ControllerBase):
    def __init__(self, smsTemplateService: SMSTemplateService = Depends()):
        
        self.smsTemplateService = smsTemplateService
    
    @get("/get", response_model=PaginatedResponseDTO[SMSTemplateResponseDTO])
    async def get(self, params: SMSTemplateFilterDTO = Depends())->PaginatedResponseDTO[SMSTemplateResponseDTO]:
        """Get SMS templates by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.smsTemplateService._build_paginated_request(params)
        result = await self.smsTemplateService.get(paginated_request)
        return result
    
    @post("/create", response_model=SMSTemplateResponseDTO)
    async def create(self, request_dto: SMSTemplateRequestDTO) -> SMSTemplateResponseDTO:
        """
        Create a new SMS template.
        POST /sms-templates/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.smsTemplateService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
            return SMSTemplateResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=SMSTemplateResponseDTO)
    async def update(self, id: UUID, request_dto: SMSTemplateRequestDTO) -> SMSTemplateResponseDTO:
        """
        Full update of an SMS template.
        PUT /sms-templates/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.smsTemplateService.update(entity)
        
        # Convert to response DTO
        if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
            return SMSTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=SMSTemplateResponseDTO)
    async def partialUpdate(self, id: UUID, updates: Dict[str, Any]) -> SMSTemplateResponseDTO:
        """
        Partial update of an SMS template.
        PATCH /sms-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.smsTemplateService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
            return SMSTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete an SMS template.
        DELETE /sms-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.smsTemplateService.delete(id)
        return {"message": "SMS template deleted successfully"}
    
    