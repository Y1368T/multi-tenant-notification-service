from typing import Optional, Dict, List, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_telegram_configuration import TenantTelegramConfiguration
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_telegram_configuration_request_dto import TenantTelegramConfigurationResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService
from notification_service.shared.exceptions.application_exceptions import ApplicationException, EntityNotFoundError
import logging

logger = logging.getLogger(__name__)


class TenantTelegramConfigurationService(BaseService[TenantTelegramConfiguration, TenantTelegramConfigurationResponseDTO]):
    """Application service for managing tenant Telegram channel configurations.

    Each configuration record maps a tenant to a Telegram bot token and optional
    rate limits. Multiple providers per tenant are supported via the ``providerName``
    + ``priority`` fields.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, TenantTelegramConfiguration, TenantTelegramConfigurationResponseDTO)
        self.uow = uow

    def _get_repository(self):
        return self.uow.tenantTelegramConfigurations

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        return []

    def _get_search_fields(self) -> Optional[List[str]]:
        return ["providerName"]

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

        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=self._get_search_fields(),
            filters=root_filters,
            relatedFilters=self._build_related_filters(params)
        )

    async def getConfigurationByTenantId(self, tenantId: UUID) -> List[TenantTelegramConfiguration]:
        """Retrieve all Telegram configurations for a given tenant."""
        async with self.uow:
            return await self.uow.tenantTelegramConfigurations.find(lambda x: x.tenantId == tenantId)

    async def getConfigurationById(self, configId: UUID) -> Optional[TenantTelegramConfiguration]:
        """Retrieve a Telegram configuration by its primary key."""
        async with self.uow:
            return await self.uow.tenantTelegramConfigurations.getById(configId)
