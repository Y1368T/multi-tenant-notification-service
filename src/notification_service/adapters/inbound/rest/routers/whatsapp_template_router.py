from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
import logging
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantFilterDTO
from notification_service.application.services.whatsapp_template_service import WhatsAppTemplateService
from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate
from notification_service.adapters.inbound.dto.whatsapp_template_request_dto import (
    WhatsAppTemplateRequestDTO,
    WhatsAppTemplateResponseDTO,
    WhatsAppTemplateFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)

@api_controller(prefix="/whatsapp-templates", tags=["WhatsApp Templates"])
class WhatsAppTemplateController(ControllerBase):
    def __init__(self, whatsappTemplateService: WhatsAppTemplateService = Depends()):
        
        self.whatsappTemplateService = whatsappTemplateService
    
    @get("/get", response_model=PaginatedResponseDTO[WhatsAppTemplateResponseDTO])
    async def get(self, params: WhatsAppTemplateFilterDTO = Depends())->PaginatedResponseDTO[WhatsAppTemplateResponseDTO]:
        """Get WhatsApp templates by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.whatsappTemplateService._build_paginated_request(params)
        result = await self.whatsappTemplateService.get(paginated_request)
        return result
    
    @post("/create", response_model=WhatsAppTemplateResponseDTO)
    async def create(self, request_dto: WhatsAppTemplateRequestDTO) -> WhatsAppTemplateResponseDTO:
        """
        Create a new WhatsApp template.
        POST /whatsapp-templates/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.whatsappTemplateService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(WhatsAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return WhatsAppTemplateResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=WhatsAppTemplateResponseDTO)
    async def update(self, id: UUID, request_dto: WhatsAppTemplateRequestDTO) -> WhatsAppTemplateResponseDTO:
        """
        Full update of an WhatsApp template.
        PUT /whatsapp-templates/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.whatsappTemplateService.update(entity)
        
        # Convert to response DTO
        if hasattr(WhatsAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return WhatsAppTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=WhatsAppTemplateResponseDTO)
    async def partialUpdate(self, id: UUID, updates: Dict[str, Any]) -> WhatsAppTemplateResponseDTO:
        """
        Partial update of an WhatsApp template.
        PATCH /whatsapp-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.whatsappTemplateService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(WhatsAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return WhatsAppTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete an WhatsApp template.
        DELETE /whatsapp-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.whatsappTemplateService.delete(id)
        return {"message": "WhatsApp template deleted successfully"}
    
    