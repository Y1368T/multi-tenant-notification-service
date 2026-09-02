from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.adapters.inbound.dto.telegram_template_request_dto import TelegramTemplateResponseDTO
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.telegram.telegram_template import TelegramTemplate
from uuid import UUID
from typing import List, Optional, Dict, Any
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService


class TelegramTemplateService(BaseService[TelegramTemplate, TelegramTemplateResponseDTO]):
    """Application service for managing Telegram message templates."""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, TelegramTemplate, TelegramTemplateResponseDTO)
        self.uow = uow

    def _get_repository(self):
        """Get Telegram templates repository."""
        return self.uow.telegramTemplates

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        related_filters: List[RelatedFilter] = []
        if hasattr(params, 'tenantId') and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="tenant",
                    field="id",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                )
            )
        return related_filters

    def _get_search_fields(self) -> Optional[List[str]]:
        return ["templateName", "serviceName"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id

        if hasattr(params, 'tenantId') and params.tenantId:
            try:
                root_filters['tenantId'] = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
            except (ValueError, AttributeError):
                root_filters['tenantId'] = params.tenantId

        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)

        related_filters = self._build_related_filters(params)
        if 'tenantId' in root_filters:
            related_filters = [rf for rf in related_filters if not (rf.relationshipPath == "tenant" and rf.field == "id")]

        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=self._get_search_fields(),
            filters=root_filters,
            relatedFilters=related_filters
        )

    async def getTemplateByFilters(self, tenantId: UUID, templateName: str, serviceName: str):
        """Get templates by tenant, name, and service name."""
        async with self.uow:
            templates = await self.uow.telegramTemplates.list(
                lambda x: x.tenantId == tenantId and x.templateName == templateName and x.serviceName == serviceName
            )
            return templates

    async def getTemplatesByTenant(self, tenantId: UUID):
        """Get all Telegram templates for a given tenant."""
        async with self.uow:
            return await self.uow.telegramTemplates.list(lambda x: x.tenantId == tenantId)
