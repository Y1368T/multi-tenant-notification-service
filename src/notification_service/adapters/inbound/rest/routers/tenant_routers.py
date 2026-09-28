from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
from notification_service.application.services.tenant_service import TenantService
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.tenant_request_dto import (
    TenantRequestDTO,
    TenantResponseDTO,
    TenantFilterDTO
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_consumer import RabbitMQConsumer
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

from notification_service.adapters.inbound.rest.dependencies.auth_dependency import get_user_context, UserContext, enforce_tenant_access, require_admin

@api_controller(prefix="/tenants", tags=["Tenants"])
class TenantController(ControllerBase):
    """Controller for tenant-related endpoints."""
    
    def __init__(self, tenantService: TenantService = Depends()):
        self.tenantService = tenantService
    @get("/get", response_model=PaginatedResponseDTO[TenantResponseDTO])
    async def get(
        self, 
        params: TenantFilterDTO = Depends()
    )->PaginatedResponseDTO[TenantResponseDTO]:
        """
        Get tenants by filters.
        GET /tenants/get?id={uuid}  → single tenant (paginated with 1 item)
        GET /tenants/get?status=active&page=1&page_size=20  → filtered list (paginated)
        """
        # Build PaginatedRequest using service method
        paginated_request = self.tenantService._build_paginated_request(params)
        
        # Call service with PaginatedRequest
        # Exceptions will be handled by global exception handlers
        result = await self.tenantService.get(paginated_request)
        return result
    
    @post("/create", response_model=TenantResponseDTO)
    async def create(
        self, 
        request_dto: TenantRequestDTO,
        _ctx: UserContext = Depends(require_admin),
    ) -> TenantResponseDTO:
        """
        Create a new tenant with validation.
        POST /tenants/create
        
        Override this method to add custom validation or business logic.
        """
        # Validate preferred communication method
        if request_dto.preferedCommunicationMethod not in ["rest", "kafka", "rabbitmq", "grpc"]:
            raise ValidationError("Invalid preferred communication method. Must be one of: rest, kafka, rabbitmq, grpc")
        
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        createdTenant = await self.tenantService.create(entity)
        # # Add custom RabbitMQ queue setup logic
        # if(createdTenant.preferedCommunicationMethod == "rabbitmq" and createdTenant.isActive and createdTenant.supportedChannels and self.rabbitmqConsumer):
        #     # Additional logic for rabbitmq preferred communication method can be added here
        #     for channel in createdTenant.supportedChannels:
        #         queueName = f"notification.{channel}.{createdTenant.prefix}"
        #         # Here you might want to initialize or configure the queue for the tenant
        #         await self.rabbitmqConsumer.ensureQueueExistsAndSubscribe(queueName=queueName,channel=channel)
        
        # Convert entity to response DTO
        if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
            return TenantResponseDTO.fromEntityWithRelations(createdTenant)
        else:
            return createdTenant
    
    @put("/{id}", response_model=TenantResponseDTO)
    async def update(
        self, 
        id: UUID, 
        request_dto: TenantRequestDTO,
        _ctx: UserContext = Depends(require_admin),
    ) -> TenantResponseDTO:
        """
        Full update of a tenant.
        PUT /tenants/{id}
        
        Override this method to add custom validation or business logic.
        """
        # Convert DTO to entity
        if hasattr(request_dto, 'toEntity'):
            entity = request_dto.toEntity()
            entity.id = id
        else:
            raise ValidationError("Request DTO must have toEntity() method")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantService.update(entity)
        
        # Convert to response DTO
        if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
            return TenantResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @patch("/{id}", response_model=TenantResponseDTO)
    async def partialUpdate(
        self, 
        id: UUID, 
        updates: Dict[str, Any],
        _ctx: UserContext = Depends(require_admin),
    ) -> TenantResponseDTO:
        """
        Partial update of a tenant.
        PATCH /tenants/{id}
        
        Override this method to add custom validation for partial updates.
        """
        # Add custom validation for partial updates
        if "preferedCommunicationMethod" in updates:
            if updates["preferedCommunicationMethod"] not in ["rest", "kafka", "rabbitmq", "grpc"]:
                raise ValidationError("Invalid preferred communication method. Must be one of: rest, kafka, rabbitmq, grpc")
        
        # Call service - exceptions will be handled by global exception handlers
        updated_entity = await self.tenantService.partialUpdate(id, updates)
        
        # Convert to response DTO
        if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
            return TenantResponseDTO.fromEntityWithRelations(updated_entity)
        else:
            return updated_entity
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(
        self, 
        id: UUID,
        _ctx: UserContext = Depends(require_admin),
    ) -> Dict[str, str]:
        """
        Delete a tenant.
        DELETE /tenants/{id}
        """
        # Call service - exceptions will be handled by global exception handlers
        await self.tenantService.delete(id)
        return {"message": "Tenant deleted successfully"}
    
    @post("/{id}/regenerate-api-key", response_model=TenantResponseDTO)
    async def regenerate_api_key(
        self,
        id: UUID,
        ctx: UserContext = Depends(get_user_context),
    ) -> TenantResponseDTO:
        """
        Regenerate API key for a tenant.
        POST /tenants/{id}/regenerate-api-key
        
        This endpoint allows:
        - Admin users to regenerate API keys for any tenant
        - Tenant users to regenerate their own API key (if id matches their tenant_id)
        
        The new API key will overwrite the existing one.
        """
        enforce_tenant_access(ctx, id)
        
        # Call service to regenerate API key
        updated_tenant = await self.tenantService.regenerate_api_key(id)
        
        # Convert to response DTO
        if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
            return TenantResponseDTO.fromEntityWithRelations(updated_tenant)
        else:
            return updated_tenant