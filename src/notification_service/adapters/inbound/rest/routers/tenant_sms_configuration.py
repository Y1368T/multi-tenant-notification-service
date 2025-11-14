from notification_service.application.services.tenant_sms_configuration_service import TenantSMSConfigurationService
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import (
    TenantSMSConfigurationRequestDto,
    TenantSMSConfigurationResponseDTO,
    TenantSMSConfigurationFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete
from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List

@api_controller(prefix="/tenant-sms-configurations", tags=["Tenant SMS Configurations"])
class TenantSMSConfigurationController(ControllerBase):
    
    def __init__(self, tenantSmsConfigurationService: TenantSMSConfigurationService = Depends()):
        
        self.tenantSmsConfigurationService = tenantSmsConfigurationService
    
    @get("/get", response_model=PaginatedResponseDTO[TenantSMSConfigurationResponseDTO])
    async def get(self, params: TenantSMSConfigurationFilterDTO = Depends()) -> PaginatedResponseDTO[TenantSMSConfigurationResponseDTO]:
        """Get tenant SMS configurations by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.tenantSmsConfigurationService._build_paginated_request(params)
        result = await self.tenantSmsConfigurationService.get(paginated_request)
        return result
    
    @post("/create", response_model=TenantSMSConfigurationResponseDTO)
    async def create(self, request_dto: TenantSMSConfigurationRequestDto) -> TenantSMSConfigurationResponseDTO:
        """
        Create a new tenant SMS configuration.
        POST /tenant-sms-configurations/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.tenantSmsConfigurationService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=TenantSMSConfigurationResponseDTO)
    async def update(self, id: UUID, request_dto: TenantSMSConfigurationRequestDto) -> TenantSMSConfigurationResponseDTO:
        """
        Full update of a tenant SMS configuration.
        PUT /tenant-sms-configurations/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantSmsConfigurationService.update(entity)
        
        # Convert to response DTO
        if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=TenantSMSConfigurationResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> TenantSMSConfigurationResponseDTO:
        """
        Partial update of a tenant SMS configuration.
        PATCH /tenant-sms-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantSmsConfigurationService.partial_update(id, updates)
        
        # Convert to response DTO
        if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a tenant SMS configuration.
        DELETE /tenant-sms-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.tenantSmsConfigurationService.delete(id)
        return {"message": "Tenant SMS configuration deleted successfully"}
    
    