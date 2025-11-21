from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
import logging
from notification_service.application.services.in_app_template_service import InAppTemplateService
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from notification_service.adapters.inbound.dto.in_app_template_request_dto import (
    InAppTemplateRequestDTO,
    InAppTemplateResponseDTO,
    InAppTemplateFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)

@api_controller(prefix="/in-app-templates", tags=["In-App Templates"])
class InAppTemplateController(ControllerBase):
    def __init__(self, inAppTemplateService: InAppTemplateService = Depends()):
        
        self.inAppTemplateService = inAppTemplateService
    
    @get("/get", response_model=PaginatedResponseDTO[InAppTemplateResponseDTO])
    async def get(self, params: InAppTemplateFilterDTO = Depends()) -> PaginatedResponseDTO[InAppTemplateResponseDTO]:
        """Get in-app templates by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.inAppTemplateService._build_paginated_request(params)
        result = await self.inAppTemplateService.get(paginated_request)
        return result
    
    @post("/create", response_model=InAppTemplateResponseDTO)
    async def create(self, request_dto: InAppTemplateRequestDTO) -> InAppTemplateResponseDTO:
        """
        Create a new in-app template.
        POST /in-app-templates/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.inAppTemplateService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(InAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return InAppTemplateResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=InAppTemplateResponseDTO)
    async def update(self, id: UUID, request_dto: InAppTemplateRequestDTO) -> InAppTemplateResponseDTO:
        """
        Full update of an in-app template.
        PUT /in-app-templates/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.inAppTemplateService.update(entity)
        
        # Convert to response DTO
        if hasattr(InAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return InAppTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=InAppTemplateResponseDTO)
    async def partialUpdate(self, id: UUID, updates: Dict[str, Any]) -> InAppTemplateResponseDTO:
        """
        Partial update of an in-app template.
        PATCH /in-app-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.inAppTemplateService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(InAppTemplateResponseDTO, 'fromEntityWithRelations'):
            return InAppTemplateResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete an in-app template.
        DELETE /in-app-templates/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.inAppTemplateService.delete(id)
        return {"message": "In-app template deleted successfully"}
    

