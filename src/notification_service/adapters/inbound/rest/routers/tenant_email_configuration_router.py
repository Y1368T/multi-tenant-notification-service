"""Tenant email configuration REST controller."""
import logging
from uuid import UUID
from datetime import datetime

from fastapi import Depends
from qena_shared_lib.http import ControllerBase, get, post, put, patch, delete, api_controller

from notification_service.application.services.tenant_email_configuration import TenantEmailConfigurationService
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.tenant_email_configuration_request_dto import (
    TenantEmailConfigurationRequestDto,
    TenantEmailConfigurationResponseDTO,
    TenantEmailConfigurationFilterDTO,
)

from notification_service.adapters.inbound.rest.dependencies.auth_dependency import require_role, UserContext

logger = logging.getLogger(__name__)


@api_controller(prefix="/tenant-email-configurations", tags=["Tenant Email Configurations"])
class TenantEmailConfigurationController(ControllerBase):
    """Controller for tenant email configuration operations."""

    def __init__(
        self, tenantEmailConfigurationService: TenantEmailConfigurationService = Depends()
    ):
        self.tenantEmailConfigurationService = tenantEmailConfigurationService

    @get("/get", response_model=PaginatedResponseDTO[TenantEmailConfigurationResponseDTO])
    async def get(
        self,
        params: TenantEmailConfigurationFilterDTO = Depends(),
        _ctx: UserContext = Depends(require_role(["super-admin"])),
    ) -> PaginatedResponseDTO[TenantEmailConfigurationResponseDTO]:
        """Get tenant email configurations by filters."""
        paginated_request = self.tenantEmailConfigurationService._build_paginated_request(
            params
        )
        result = await self.tenantEmailConfigurationService.get(paginated_request)
        return result

    @post("/create", response_model=TenantEmailConfigurationResponseDTO)
    async def create(
        self,
        requestDto: TenantEmailConfigurationRequestDto,
        _ctx: UserContext = Depends(require_role(["super-admin"])),
    ) -> TenantEmailConfigurationResponseDTO:
        """Create a new tenant email configuration."""
        entity = requestDto.toEntity()
        created = await self.tenantEmailConfigurationService.create(entity)
        return TenantEmailConfigurationResponseDTO.fromEntityWithRelations(created)

    @put("/{id}", response_model=TenantEmailConfigurationResponseDTO)
    async def update(
        self,
        id: UUID,
        requestDto: TenantEmailConfigurationRequestDto,
        _ctx: UserContext = Depends(require_role(["super-admin"])),
    ) -> TenantEmailConfigurationResponseDTO:
        """Full update of a tenant email configuration."""
        entity = requestDto.toEntity()
        entity.id = id
        entity.updatedAt = datetime.utcnow()
        updated = await self.tenantEmailConfigurationService.update(entity)
        return TenantEmailConfigurationResponseDTO.fromEntityWithRelations(updated)

    @patch("/{id}", response_model=TenantEmailConfigurationResponseDTO)
    async def partialUpdate(
        self,
        id: UUID,
        updates: dict,
        _ctx: UserContext = Depends(require_role(["super-admin"])),
    ) -> TenantEmailConfigurationResponseDTO:
        """Partial update of a tenant email configuration."""
        updated = await self.tenantEmailConfigurationService.partialUpdate(id, updates)
        return TenantEmailConfigurationResponseDTO.fromEntityWithRelations(updated)

    @delete("/{id}")
    async def deleteConfiguration(
        self,
        id: UUID,
        _ctx: UserContext = Depends(require_role(["super-admin"])),
    ):
        """Delete a tenant email configuration."""
        await self.tenantEmailConfigurationService.delete(id)
        return {"message": "Tenant email configuration deleted successfully"}
