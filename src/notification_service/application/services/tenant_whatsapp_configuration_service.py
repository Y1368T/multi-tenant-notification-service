from typing import Optional, Dict, List, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.domain.value_objects.providers import WhatsAppProvider
from notification_service.infrastructure import RedisCache
from notification_service.infrastructure.providers.whatsapp.meta_cloud_provider import WhatsAppMetaCloudProvider
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_whatsapp_confuguration_request_dto import TenantWhatsAppConfigurationResponseDTO
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
class TenantWhatsAppConfigurationService(BaseService[TenantWhatsAppConfiguration, TenantWhatsAppConfigurationResponseDTO]):

    def __init__(
        self,
        uow: IUnitOfWork,
        meta_cloud_service: WhatsAppMetaCloudProvider,
        redis: RedisCache,
    ):
        super().__init__(uow, TenantWhatsAppConfiguration, TenantWhatsAppConfigurationResponseDTO)
        self.uow = uow
        self._handlers = {
            WhatsAppProvider.META_CLOUD: meta_cloud_service,
        }
        self.redis = redis

    def _get_repository(self):
        """Get tenant WhatsApp configurations repository."""
        return self.uow.tenantWhatsAppConfigurations

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenant WhatsApp configurations."""
        # Tenant WhatsApp configurations don't have related filters by default
        return []

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for tenant WhatsApp configurations."""
        return ["providerName"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for tenant WhatsApp configurations."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id

        if hasattr(params, 'tenantId') and params.tenantId:
            try:
                tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                root_filters['tenantId'] = tenant_id_value
            except (ValueError, AttributeError):
                root_filters['tenantId'] = params.tenantId

        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)

        # Build related filters
        related_filters = self._build_related_filters(params)

        # Get search fields
        search_fields = self._get_search_fields()

        # Build and return PaginatedRequest
        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=search_fields,
            filters=root_filters,
            relatedFilters=related_filters
        )

    async def getConfigurationByTenantId(self, tenantId: UUID) -> TenantWhatsAppConfiguration:
        """Retrieve WhatsApp configuration for a given tenant.

        Args:
            tenantId: Tenant identifier

        Returns:
            TenantWhatsAppConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.tenantWhatsAppConfigurations.find(lambda x: x.tenantId == tenantId)
            return config

    # Keep old methods for backward compatibility
    async def createConfiguration(self, config: TenantWhatsAppConfiguration) -> TenantWhatsAppConfiguration:
        """Create a new WhatsApp configuration (deprecated - use create() instead)."""
        try:
            async with self.uow:
                created_config = await self.uow.tenantWhatsAppConfigurations.create(config)
                await self.uow.commit()
                cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                await self.redis.set(cache_key, created_config.__dict__, expire=60*60*24)
                return created_config
        except Exception as e:
            raise ApplicationException(
                f"Error creating WhatsApp configuration: {e}",
                code="ERROR_CREATING_WHATSAPP_CONFIGURATION",
                details={"config": config}
            )
        finally:
            if config:
                cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config

    # Keep old methods for backward compatibility
    async def updateConfiguration(self, config: TenantWhatsAppConfiguration) -> TenantWhatsAppConfiguration:
        """Update an existing WhatsApp configuration (deprecated - use update() instead)."""
        try:
            async with self.uow:
                updated_config = await self.uow.tenantWhatsAppConfigurations.update(config)
                await self.uow.commit()
                cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, updated_config.__dict__, expire=60*60*24)
                return updated_config
        except Exception as e:
            raise ApplicationException(
                f"Error updating WhatsApp configuration: {e}",
                code="ERROR_UPDATING_WHATSAPP_CONFIGURATION",
                details={"configId": config.id}
            )
        finally:
            if config:
                cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config

    async def deleteConfiguration(self, configId: UUID) -> None:
        """Delete an existing WhatsApp configuration (deprecated - use delete() instead)."""

        async with self.uow:
            try:
                config = await self.uow.tenantWhatsAppConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantWhatsAppConfigurations.delete(configId)
                    await self.uow.commit()
            except Exception as e:
                logger.error(f"Error deleting WhatsApp configuration: {e}")
                raise ApplicationException(
                    f"Error deleting WhatsApp configuration: {e}",
                    code="ERROR_DELETING_WHATSAPP_CONFIGURATION",
                    details={"configId": configId}
                )
            finally:
                if config:
                    cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    return config

    async def partialUpdate(self, configId: UUID, updates: Dict[str, Any]) -> TenantWhatsAppConfiguration:
        """Partial update of an existing WhatsApp configuration (deprecated - use partialUpdate() instead)."""
        try:
            async with self.uow:
                config = await self.uow.tenantWhatsAppConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantWhatsAppConfigurations.partialUpdate(configId, updates)
                    await self.uow.commit()
                    await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                    return config
        except Exception as e:
            raise ApplicationException(
                f"Error partial updating WhatsApp configuration: {e}",
                code="ERROR_PARTIAL_UPDATING_WHATSAPP_CONFIGURATION",
                details={"configId": configId}
            )
        finally:
            if config:
                cache_key = f"tenant_config:whatsapp:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config

    async def getConfigurationById(self, configId: UUID) -> Optional[TenantWhatsAppConfiguration]:
        """Retrieve WhatsApp configuration by its ID (custom method)."""
        async with self.uow:
            config = await self.uow.tenantWhatsAppConfigurations.getById(configId)
            return config

    async def doACircuitBreakerCheck(self, config: TenantWhatsAppConfiguration, provider: WhatsAppProvider) -> bool:
        """Perform a circuit breaker check for WhatsApp configurations.

        Returns:
            bool: True if the circuit is closed, False if open
        """
        match provider:
            case WhatsAppProvider.META_CLOUD:
                # Placeholder: implement Meta Cloud-specific circuit breaker logic if needed
                return True
            case _:
                return False
        return False

    # Keep old method for backward compatibility
    async def getAllConfigurationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantWhatsAppConfigurationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)
