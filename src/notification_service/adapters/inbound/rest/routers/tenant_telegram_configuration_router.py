from fastapi import Depends
from uuid import UUID
from typing import Dict, Any
import logging

from notification_service.application.services.tenant_telegram_configuration_service import TenantTelegramConfigurationService
from notification_service.adapters.inbound.dto.tenant_telegram_configuration_request_dto import (
    TenantTelegramConfigurationRequestDto,
    TenantTelegramConfigurationResponseDTO,
    TenantTelegramConfigurationFilterDTO,
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)


@api_controller(prefix="/tenant-telegram-configurations", tags=["Tenant Telegram Configurations"])
class TenantTelegramConfigurationController(ControllerBase):
    """Manage per-tenant Telegram provider configurations.

    Each configuration record stores the Telegram **bot token** and optional
    rate limits for a specific provider. A tenant may have multiple
    configurations with different priorities for fallback routing.

    - **GET /get** – paginated list with filters
    - **POST /create** – register a new bot token for a tenant
    - **PUT /{id}** – full replacement
    - **PATCH /{id}** – partial update
    - **DELETE /{id}** – remove configuration
    """

    def __init__(
        self,
        tenantTelegramConfigurationService: TenantTelegramConfigurationService = Depends()
    ):
        self.tenantTelegramConfigurationService = tenantTelegramConfigurationService

    @get("/get", response_model=PaginatedResponseDTO[TenantTelegramConfigurationResponseDTO])
    async def get(
        self, params: TenantTelegramConfigurationFilterDTO = Depends()
    ) -> PaginatedResponseDTO[TenantTelegramConfigurationResponseDTO]:
        """List tenant Telegram configurations with optional filters.

        **Query parameters:**
        - `tenantId` – filter by tenant UUID
        - `isActive` – filter by active status
        - `providerName` – filter by provider name
        - `page`, `pageSize`, `sortBy`, `sortDirection` – pagination controls
        """
        paginated_request = self.tenantTelegramConfigurationService._build_paginated_request(params)
        return await self.tenantTelegramConfigurationService.get(paginated_request)

    @post("/create", response_model=TenantTelegramConfigurationResponseDTO)
    async def create(
        self, request_dto: TenantTelegramConfigurationRequestDto
    ) -> TenantTelegramConfigurationResponseDTO:
        """Register a Telegram bot configuration for a tenant.

        The `config` field must contain the bot token:

        ```json
        {
          "tenantId": "...",
          "providerName": "telegram",
          "priority": 1,
          "config": { "bot_token": "123456:ABC-DEF..." }
        }
        ```
        """
        if not hasattr(request_dto, 'toEntity'):
            raise ValidationError("Request DTO must have toEntity() method")
        entity = request_dto.toEntity()
        created = await self.tenantTelegramConfigurationService.create(entity)
        return TenantTelegramConfigurationResponseDTO.fromEntityWithRelations(created)

    @put("/{id}", response_model=TenantTelegramConfigurationResponseDTO)
    async def update(
        self, id: UUID, request_dto: TenantTelegramConfigurationRequestDto
    ) -> TenantTelegramConfigurationResponseDTO:
        """Fully replace a tenant Telegram configuration."""
        if not hasattr(request_dto, 'toEntity'):
            raise ValidationError("Request DTO must have toEntity() method")
        entity = request_dto.toEntity()
        entity.id = id
        updated = await self.tenantTelegramConfigurationService.update(entity)
        return TenantTelegramConfigurationResponseDTO.fromEntityWithRelations(updated)

    @patch("/{id}", response_model=TenantTelegramConfigurationResponseDTO)
    async def partialUpdate(
        self, id: UUID, updates: Dict[str, Any]
    ) -> TenantTelegramConfigurationResponseDTO:
        """Partially update a tenant Telegram configuration.

        Example – disable a configuration without deleting it:

        ```json
        { "isActive": false }
        ```
        """
        updated = await self.tenantTelegramConfigurationService.partialUpdate(id, updates)
        return TenantTelegramConfigurationResponseDTO.fromEntityWithRelations(updated)

    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """Remove a tenant Telegram configuration."""
        await self.tenantTelegramConfigurationService.delete(id)
        return {"message": "Tenant Telegram configuration deleted successfully"}
