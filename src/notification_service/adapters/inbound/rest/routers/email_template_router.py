"""Email template REST controller."""
import logging
from uuid import UUID
from datetime import datetime

from fastapi import Depends
from qena_shared_lib.http import ControllerBase, get, post, put, patch, delete, api_controller

from notification_service.application.services.email_template_service import EmailTemplateService
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.email_template_request_dto import (
    EmailTemplateRequestDTO,
    EmailTemplateResponseDTO,
    EmailTemplateFilterDTO,
)

logger = logging.getLogger(__name__)


@api_controller(prefix="/email-templates", tags=["Email Templates"])
class EmailTemplateController(ControllerBase):
    """Controller for email template operations."""

    def __init__(self, emailTemplateService: EmailTemplateService = Depends()):
        self.emailTemplateService = emailTemplateService

    @get("/get", response_model=PaginatedResponseDTO[EmailTemplateResponseDTO])
    async def get(
        self, params: EmailTemplateFilterDTO = Depends()
    ) -> PaginatedResponseDTO[EmailTemplateResponseDTO]:
        """Get Email templates by filters."""
        paginated_request = self.emailTemplateService._build_paginated_request(params)
        result = await self.emailTemplateService.get(paginated_request)
        return result

    @post("/create", response_model=EmailTemplateResponseDTO)
    async def create(
        self, requestDto: EmailTemplateRequestDTO
    ) -> EmailTemplateResponseDTO:
        """Create a new email template."""
        entity = requestDto.toEntity()
        created = await self.emailTemplateService.create(entity)
        return EmailTemplateResponseDTO.fromEntityWithRelations(created)

    @put("/{id}", response_model=EmailTemplateResponseDTO)
    async def update(
        self, id: UUID, requestDto: EmailTemplateRequestDTO
    ) -> EmailTemplateResponseDTO:
        """Full update of an email template."""
        entity = requestDto.toEntity()
        entity.id = id
        entity.updatedAt = datetime.utcnow()
        updated = await self.emailTemplateService.update(entity)
        return EmailTemplateResponseDTO.fromEntityWithRelations(updated)

    @patch("/{id}", response_model=EmailTemplateResponseDTO)
    async def partialUpdate(
        self, id: UUID, updates: dict
    ) -> EmailTemplateResponseDTO:
        """Partial update of an email template."""
        updated = await self.emailTemplateService.partialUpdate(id, updates)
        return EmailTemplateResponseDTO.fromEntityWithRelations(updated)

    @delete("/{id}")
    async def deleteTemplate(self, id: UUID):
        """Delete an email template."""
        await self.emailTemplateService.delete(id)
        return {"message": "Email template deleted successfully"}
