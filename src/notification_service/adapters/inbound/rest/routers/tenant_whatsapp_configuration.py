from notification_service.application.services.tenant_whatsapp_configuration_service import TenantWhatsAppConfigurationService
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.adapters.inbound.dto.tenant_whatsapp_confuguration_request_dto import (
    TenantWhatsAppConfigurationRequestDto,
    TenantWhatsAppConfigurationResponseDTO,
    TenantWhatsAppConfigurationFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete
from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
from notification_service.adapters.inbound.dependencies import require_role

@api_controller(prefix="/tenant-whatsapp-configurations", tags=["Tenant WhatsApp Configurations"])
class TenantWhatsAppConfigurationController(ControllerBase):
    
    def __init__(self, tenantWhatsAppConfigurationService: TenantWhatsAppConfigurationService = Depends()):
        
        self.tenantWhatsAppConfigurationService = tenantWhatsAppConfigurationService
    
    @get("/get", response_model=PaginatedResponseDTO[TenantWhatsAppConfigurationResponseDTO])
    async def get(
        self, 
        params: TenantWhatsAppConfigurationFilterDTO = Depends()
    ) -> PaginatedResponseDTO[TenantWhatsAppConfigurationResponseDTO]:
        """Get tenant WhatsApp configurations by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.tenantWhatsAppConfigurationService._build_paginated_request(params)
        result = await self.tenantWhatsAppConfigurationService.get(paginated_request)
        return result
    
    @post("/create", response_model=TenantWhatsAppConfigurationResponseDTO, dependencies=[Depends(require_role(["super-admin"]))])
    async def create(
        self, 
        request_dto: TenantWhatsAppConfigurationRequestDto
    ) -> TenantWhatsAppConfigurationResponseDTO:
        """
        Create a new tenant WhatsApp configuration.
        POST /tenant-whatsapp-configurations/create
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        created_entity = await self.tenantWhatsAppConfigurationService.create(entity)
        
        # Convert entity to response DTO
        if hasattr(TenantWhatsAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantWhatsAppConfigurationResponseDTO.fromEntityWithRelations(created_entity)
        else:
            return created_entity
    
    @put("/{id}", response_model=TenantWhatsAppConfigurationResponseDTO, dependencies=[Depends(require_role(["super-admin"]))])
    async def update(
        self, 
        id: UUID, 
        request_dto: TenantWhatsAppConfigurationRequestDto
    ) -> TenantWhatsAppConfigurationResponseDTO:
        """
        Full update of a tenant WhatsApp configuration.
        PUT /tenant-whatsapp-configurations/{id}
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantWhatsAppConfigurationService.updateConfiguration(entity)
        
        # Convert to response DTO
        if hasattr(TenantWhatsAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantWhatsAppConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=TenantWhatsAppConfigurationResponseDTO, dependencies=[Depends(require_role(["super-admin"]))])
    async def partialUpdate(
        self, 
        id: UUID, 
        updates: Dict[str, Any]
    ) -> TenantWhatsAppConfigurationResponseDTO:
        """
        Partial update of a tenant WhatsApp configuration.
        PATCH /tenant-whatsapp-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantWhatsAppConfigurationService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(TenantWhatsAppConfigurationResponseDTO, 'fromEntityWithRelations'):
            return TenantWhatsAppConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str], dependencies=[Depends(require_role(["super-admin"]))])
    async def delete(
        self, 
        id: UUID
    ) -> Dict[str, str]:
        """
        Delete a tenant WhatsApp configuration.
        DELETE /tenant-whatsapp-configurations/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.tenantWhatsAppConfigurationService.delete(id)
        return {"message": "Tenant WhatsApp configuration deleted successfully"}
    
    