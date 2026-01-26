"""Tenant email configuration service following the same pattern as other configuration services."""
from uuid import UUID
from typing import Optional, List, Dict, Any

from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.domain.value_objects.providers import EmailProvider
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_email_configuration_request_dto import (
    TenantEmailConfigurationResponseDTO,
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp,
)


class TenantEmailConfigurationService(
    BaseService[TenantEmailConfiguration, TenantEmailConfigurationResponseDTO]
):
    """Service for managing tenant email configurations."""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, TenantEmailConfiguration, TenantEmailConfigurationResponseDTO)
        self.uow = uow

    def _get_repository(self):
        """Get tenant email configurations repository."""
        return self.uow.tenantEmailConfigurations

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
        if hasattr(params, "providerName") and params.providerName:
            filters["providerName"] = params.providerName
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenant email configurations."""
        # No related filters needed (tenantId is a direct field)
        return []

    def _get_includes(self) -> List[str]:
        """Get relationship paths to eager load."""
        return ["tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for tenant email configurations."""
        return ["providerName", "tenant.name", "tenant.prefix"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for tenant email configurations."""
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

    async def getConfigurationByTenantId(
        self, tenant_id: UUID
    ) -> Optional[TenantEmailConfiguration]:
        """Retrieve email configuration for a given tenant.

        Args:
            tenant_id: Tenant identifier
        Returns:
            TenantEmailConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.tenantEmailConfigurations.firstOrDefault(
                lambda c: c.tenantId == tenant_id and c.isActive == True
            )
            return config

    async def createConfiguration(
        self, config: TenantEmailConfiguration
    ) -> TenantEmailConfiguration:
        """Create a new email configuration for a tenant."""
        return await self.create(config)

    async def updateConfiguration(
        self, config: TenantEmailConfiguration
    ) -> TenantEmailConfiguration:
        """Update an existing email configuration for a tenant."""
        return await self.update(config)

    async def deleteConfiguration(self, config_id: UUID) -> None:
        """Delete an existing email configuration for a tenant."""
        await self.delete(config_id)

    async def doACircuitBreakerCheck(
        self, config: TenantEmailConfiguration, provider: EmailProvider
    ) -> bool:
        """Perform a circuit breaker check for email configurations.

        Returns:
            True if the provider is healthy, False otherwise
        """
        # Placeholder implementation for circuit breaker logic
        match provider:
            case EmailProvider.SMTP:
                # SMTP-specific circuit breaker logic
                pass
            case EmailProvider.SENDGRID:
                # SendGrid-specific circuit breaker logic
                pass
        return True
