from fastapi import Depends
from uuid import UUID
from typing import Dict, Any
import logging

from notification_service.application.services.telegram_template_service import TelegramTemplateService
from notification_service.adapters.inbound.dto.telegram_template_request_dto import (
    TelegramTemplateRequestDTO,
    TelegramTemplateResponseDTO,
    TelegramTemplateFilterDTO,
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)


@api_controller(prefix="/telegram-templates", tags=["Telegram Templates"])
class TelegramTemplateController(ControllerBase):
    """CRUD controller for Telegram message templates.

    Templates define the localized text content sent to Telegram chat IDs.
    Each template belongs to a tenant and can be versioned.

    - **GET /get** – paginated list with filters (tenantId, isActive, search)
    - **POST /create** – create a new template
    - **PUT /{id}** – full replacement
    - **PATCH /{id}** – partial update (e.g. toggle isActive)
    - **DELETE /{id}** – permanently remove a template
    """

    def __init__(self, telegramTemplateService: TelegramTemplateService = Depends()):
        self.telegramTemplateService = telegramTemplateService

    @get("/get", response_model=PaginatedResponseDTO[TelegramTemplateResponseDTO])
    async def get(
        self, params: TelegramTemplateFilterDTO = Depends()
    ) -> PaginatedResponseDTO[TelegramTemplateResponseDTO]:
        """List Telegram templates with optional filters.

        **Query parameters:**
        - `tenantId` – filter by tenant UUID
        - `isActive` – filter by active status
        - `search` – text search across templateName and serviceName
        - `page`, `pageSize`, `sortBy`, `sortDirection` – pagination controls
        """
        paginated_request = self.telegramTemplateService._build_paginated_request(params)
        return await self.telegramTemplateService.get(paginated_request)

    @post("/create", response_model=TelegramTemplateResponseDTO)
    async def create(self, request_dto: TelegramTemplateRequestDTO) -> TelegramTemplateResponseDTO:
        """Create a new Telegram message template.

        **Content field** accepts a dictionary mapping language codes (e.g. `"en"`, `"am"`)
        to template strings. Placeholders use `{variableName}` syntax.

        ```json
        {
          "templateName": "WelcomeMsg",
          "tenantId": "...",
          "serviceName": "Onboarding",
          "version": 1,
          "isActive": true,
          "content": {
            "en": "Hello {userName}, welcome to {serviceName}!"
          }
        }
        ```
        """
        if not hasattr(request_dto, 'toEntity'):
            raise ValidationError("Request DTO must have toEntity() method")
        entity = request_dto.toEntity()
        created = await self.telegramTemplateService.create(entity)
        return TelegramTemplateResponseDTO.fromEntityWithRelations(created)

    @put("/{id}", response_model=TelegramTemplateResponseDTO)
    async def update(self, id: UUID, request_dto: TelegramTemplateRequestDTO) -> TelegramTemplateResponseDTO:
        """Fully replace a Telegram template by ID."""
        if not hasattr(request_dto, 'toEntity'):
            raise ValidationError("Request DTO must have toEntity() method")
        entity = request_dto.toEntity()
        entity.id = id
        updated = await self.telegramTemplateService.update(entity)
        return TelegramTemplateResponseDTO.fromEntityWithRelations(updated)

    @patch("/{id}", response_model=TelegramTemplateResponseDTO)
    async def partialUpdate(self, id: UUID, updates: Dict[str, Any]) -> TelegramTemplateResponseDTO:
        """Partially update a Telegram template.

        Only the supplied fields are changed. Example – deactivate a template:

        ```json
        { "isActive": false }
        ```
        """
        updated = await self.telegramTemplateService.partialUpdate(id, updates)
        return TelegramTemplateResponseDTO.fromEntityWithRelations(updated)

    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """Permanently delete a Telegram template."""
        await self.telegramTemplateService.delete(id)
        return {"message": "Telegram template deleted successfully"}
