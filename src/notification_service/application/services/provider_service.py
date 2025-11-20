from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.providers_supported import Provider
from uuid import UUID
from typing import List, Optional, Dict, Any
from notification_service.adapters.inbound.dto.provider_supported_dto import TestRequestDto, ProviderResponseDTO
from notification_service.infrastructure.providers.in_app.fcm_provider import FCMProvider
from notification_service.infrastructure.providers.sms.kifiyaSmsProvider import KifiyaSMSProvider
from notification_service.infrastructure.providers.sms.kannel_sms_provider import KannelSMSProvider
from notification_service.infrastructure.providers.sms.jasmin_sms_provider import JasminSMSProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.application.services.base_service import BaseService
from pydantic import ValidationError


class ProviderService(BaseService[Provider, ProviderResponseDTO]):
    
    def __init__(
        self,
        uow: IUnitOfWork,
        kifiyaSmsProvider: KifiyaSMSProvider,
        afromessageSmsProvider: AfromessageSMSProvider,
        kannelSmsProvider: KannelSMSProvider,
        jasminSmsProvider: JasminSMSProvider,
        fcmProvider: FCMProvider,
    ):
        super().__init__(uow, Provider, ProviderResponseDTO)
        self.uow = uow
        self.kifiyaSmsProvider = kifiyaSmsProvider
        self.afromessageSmsProvider = afromessageSmsProvider
        self.kannelSmsProvider = kannelSmsProvider
        self.jasminSmsProvider = jasminSmsProvider
        self.fcmProvider = fcmProvider
    def _get_repository(self):
        """Get providers repository."""
        return self.uow.providers
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'channel') and params.channel:
            filters["channel"] = params.channel
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for providers."""
        # Providers don't have related filters by default
        return []
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for providers."""
        return ["providerName", "displayName", "channel"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for providers."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
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
    
    # Keep old method for backward compatibility
    async def create_provider(self, provider: Provider) -> Provider:
        """Create a new provider (deprecated - use create() instead)."""
        return await self.create(provider)
    
    async def get_all(self) -> list[Provider]:
        """Get all providers (deprecated - use get() instead)."""
        async with self.uow:
            providers = await self.uow.providers.list()
            return providers
    
    async def get_providers_by_channel(self, channel: str) -> list[Provider]:
        """Get providers by channel (custom method)."""
        async with self.uow:
            providers = await self.uow.providers.list(lambda p: p.channel == channel)
            return providers
    
    async def get_provider_by_name(self, name: str) -> Provider:
        """Get provider by name (custom method)."""
        async with self.uow:
            provider = await self.uow.providers.firstOrDefault(lambda p: p.providerName == name)
            return provider
    async def test_provider(self, dto:TestRequestDto)->ProviderTestResponse:
        # Implement the logic to test the provider with the given configuration
        match dto.channel:
            case "sms":
                # Add SMS provider testing logic here
                match dto.provider_name:
                    case "kifiya":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.kifiyaSmsProvider.test(provider_config, dto.address)
                    case "afromessage":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.afromessageSmsProvider.test(provider_config, dto.address)
                    case "kannel":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.kannelSmsProvider.test(provider_config, dto.address)
                    case "jasmin":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.jasminSmsProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.provider_name}")
            case "inapp":
                match dto.provider_name:
                    case "fcm":
                        # Extract nested config if it exists, otherwise use config directly
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.fcmProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.provider_name}")
                
            case _:
                raise ValueError(f"Unsupported channel: {dto.channel}")
            