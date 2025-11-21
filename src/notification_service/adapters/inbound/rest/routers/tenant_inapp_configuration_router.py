from notification_service.application.services.tenant_inapp_configuration_service import TenantInAppConfigurationService
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.adapters.inbound.dto.tenant_inapp_configuration_request_dto import (
    TenantInAppConfigurationRequestDto,
    TenantInAppConfigurationResponseDTO,
    TenantInAppConfigurationFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete
from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List

@api_controller(prefix="/tenant-inapp-configurations", tags=["Tenant In-App Configurations"])
class TenantInAppConfigurationController(ControllerBase):
    
    def __init__(self, tenantInAppConfigurationService: TenantInAppConfigurationService = Depends()):
        
        self.tenantInAppConfigurationService = tenantInAppConfigurationService
    
    @get("/get", response_model=PaginatedResponseDTO[TenantInAppConfigurationResponseDTO])
    async def get(self, params: TenantInAppConfigurationFilterDTO = Depends()) -> PaginatedResponseDTO[TenantInAppConfigurationResponseDTO]:
        """Get tenant in-app configurations by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.tenantInAppConfigurationService._build_paginated_request(params)
        result = await self.tenantInAppConfigurationService.get(paginated_request)
        return result
    
    @post("/create", response_model=TenantInAppConfigurationResponseDTO)
    async def create(self, request_dto: TenantInAppConfigurationRequestDto) -> TenantInAppConfigurationResponseDTO:
        """
        Create a new tenant in-app configuration.
        POST /tenant-inapp-configurations/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.tenantInAppConfigurationService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(TenantInAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantInAppConfigurationResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=TenantInAppConfigurationResponseDTO)
    async def update(self, id: UUID, request_dto: TenantInAppConfigurationRequestDto) -> TenantInAppConfigurationResponseDTO:
        """
        Full update of a tenant in-app configuration.
        PUT /tenant-inapp-configurations/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantInAppConfigurationService.update(entity)
        
        # Convert to response DTO
        if hasattr(TenantInAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantInAppConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=TenantInAppConfigurationResponseDTO)
    async def partialUpdate(self, id: UUID, updates: Dict[str, Any]) -> TenantInAppConfigurationResponseDTO:
        """
        Partial update of a tenant in-app configuration.
        PATCH /tenant-inapp-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantInAppConfigurationService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(TenantInAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantInAppConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a tenant in-app configuration.
        DELETE /tenant-inapp-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.tenantInAppConfigurationService.delete(id)
        return {"message": "Tenant in-app configuration deleted successfully"}
    

