from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from qena_shared_lib.http import ControllerBase, api_controller, get, post, delete, put, patch
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.domain.entities.providers_supported import Provider
from notification_service.adapters.inbound.dto.provider_supported_dto import (
    ProviderSupportedDTO,
    ProviderResponseDTO,
    ProviderFilterDTO,
    TestRequestDto
)
from notification_service.shared.exceptions.application_exceptions import ValidationError
from uuid import UUID
from typing import Dict, Any
from fastapi import Depends

@api_controller(prefix="/provider-supported", tags=["Provider Supported"])
class ProviderSupportedController(ControllerBase):
    
    def __init__(self, providerService: ProviderService = Depends()):
        self.providerService = providerService
    
    @get("/get", response_model=PaginatedResponseDTO[ProviderResponseDTO])
    async def get(self, params: ProviderFilterDTO = Depends()) -> PaginatedResponseDTO[ProviderResponseDTO]:
        """Get providers by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.providerService._build_paginated_request(params)
        
        # Call service with PaginatedRequest
        result = await self.providerService.get(paginated_request)
        return result
    
    
    @post("/create", response_model=ProviderResponseDTO)
    async def create(self, request_dto: ProviderSupportedDTO) -> ProviderResponseDTO:
        """
        Create a new provider.
        POST /provider-supported/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.providerService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
            return ProviderResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=ProviderResponseDTO)
    async def update(self, id: UUID, request_dto: ProviderSupportedDTO) -> ProviderResponseDTO:
        """
        Full update of a provider.
        PUT /provider-supported/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.providerService.update(entity)
        
        # Convert to response DTO
        if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
            return ProviderResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=ProviderResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> ProviderResponseDTO:
        """
        Partial update of a provider.
        PATCH /provider-supported/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.providerService.partial_update(id, updates)
        
        # Convert to response DTO
        if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
            return ProviderResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a provider.
        DELETE /provider-supported/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.providerService.delete(id)
        return {"message": "Provider deleted successfully"}
    
    @post("/test", response_model=ProviderTestResponse)
    async def test_provider(self, dto: TestRequestDto) -> ProviderTestResponse:
        """Test a provider (custom endpoint)."""
        return await self.providerService.test_provider(dto)
    