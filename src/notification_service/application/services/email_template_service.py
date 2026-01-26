"""Email template service following the same pattern as SMSTemplateService."""
from uuid import UUID
from typing import Optional, List, Dict, Any

from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.email_template_request_dto import EmailTemplateResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp,
)


class EmailTemplateService(BaseService[EmailTemplate, EmailTemplateResponseDTO]):
    """Service for managing email templates."""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, EmailTemplate, EmailTemplateResponseDTO)
        self.uow = uow

    def _get_repository(self):
        """Get Email templates repository."""
        return self.uow.emailTemplates

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, "isActive") and params.isActive is not None:
            filters["isActive"] = params.isActive
        if hasattr(params, "tenantId") and params.tenantId:
            filters["tenantId"] = (
                UUID(params.tenantId)
                if isinstance(params.tenantId, str)
                else params.tenantId
            )
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for Email templates."""
        # No related filters needed for templates (tenantId is a direct field)
        return []

    def _get_includes(self) -> List[str]:
        """Get relationship paths to eager load for Email templates."""
        return ["tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for Email templates."""
        return ["templateName", "serviceName", "subject", "tenant.name", "tenant.prefix"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for Email templates."""
        # Build root filters
        root_filters = {}
        if hasattr(params, "id") and params.id:
            try:
                root_filters["id"] = (
                    UUID(params.id) if isinstance(params.id, str) else params.id
                )
            except (ValueError, AttributeError):
                root_filters["id"] = params.id

        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)

        # Build related filters
        related_filters = self._build_related_filters(params)

        # Get search fields
        search_fields = self._get_search_fields()

        # Get includes
        includes = self._get_includes()

        # Build and return PaginatedRequest
        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=search_fields,
            filters=root_filters,
            relatedFilters=related_filters,
            includes=includes,
        )

    async def getTemplateByName(
        self, tenantId: UUID, templateName: str, serviceName: str
    ) -> Optional[EmailTemplate]:
        """Get template by name, tenant, and service."""
        async with self.uow:
            template = await self.uow.emailTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantId
                and t.templateName == templateName
                and t.serviceName == serviceName
            )
            return template

    async def createTemplate(self, template: EmailTemplate) -> EmailTemplate:
        """Create a new email template."""
        return await self.create(template)

    async def updateTemplate(self, template: EmailTemplate) -> EmailTemplate:
        """Update an existing email template."""
        return await self.update(template)

    async def deleteTemplate(self, templateId: UUID) -> None:
        """Delete an email template."""
        await self.delete(templateId)
