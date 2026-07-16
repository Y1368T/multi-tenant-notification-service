from datetime import datetime

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.providers_supported import Provider
from uuid import UUID
from typing import List, Optional, Dict, Any
from notification_service.adapters.inbound.dto.provider_supported_dto import TestRequestDto, ProviderResponseDTO
from notification_service.infrastructure.providers.in_app.fcm_provider import FCMProvider
from notification_service.infrastructure.providers.sms.kifiyaSmsProvider import KifiyaSMSProvider
from notification_service.infrastructure.providers.sms.jasmin_sms_provider import JasminSMSProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.infrastructure.providers.email.smtp_provider import SMTPProvider
from notification_service.infrastructure.providers.telegram.telegram_provider import TelegramProvider as TelegramProviderImpl
#new
from notification_service.infrastructure.providers.whatsapp.meta_cloud_provider import WhatsAppMetaCloudProvider
#new
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.application.services.base_service import BaseService
from pydantic import ValidationError
# added for provider-health persistence
from sqlalchemy import update as sqlUpdate
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
import logging

logger = logging.getLogger(__name__)


class ProviderService(BaseService[Provider, ProviderResponseDTO]):
    
    def __init__(
        self,
        uow: IUnitOfWork,
        kifiyaSmsProvider: KifiyaSMSProvider,
        afromessageSmsProvider: AfromessageSMSProvider,
        jasminSmsProvider: JasminSMSProvider,
        fcmProvider: FCMProvider,
        smtpProvider: SMTPProvider,
        telegramProvider: TelegramProviderImpl = None,
        metaCloudProvider: WhatsAppMetaCloudProvider = None
        
    ):
        super().__init__(uow, Provider, ProviderResponseDTO)
        self.uow = uow
        self.kifiyaSmsProvider = kifiyaSmsProvider
        self.afromessageSmsProvider = afromessageSmsProvider
        self.jasminSmsProvider = jasminSmsProvider
        self.fcmProvider = fcmProvider
        self.smtpProvider = smtpProvider
        self.telegramProvider = telegramProvider
        self.metaCloudProvider = metaCloudProvider
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
    async def createProvider(self, provider: Provider) -> Provider:
        """Create a new provider (deprecated - use create() instead)."""
        return await self.create(provider)
    
    async def getAll(self) -> list[Provider]:
        """Get all providers (deprecated - use get() instead)."""
        async with self.uow:
            providers = await self.uow.providers.list()
            return providers
    
    async def getProvidersByChannel(self, channel: str) -> list[Provider]:
        """Get providers by channel (custom method)."""
        async with self.uow:
            providers = await self.uow.providers.list(lambda p: p.channel == channel)
            return providers
    
    async def getProviderByName(self, name: str) -> Provider:
        """Get provider by name (custom method)."""
        async with self.uow:
            provider = await self.uow.providers.firstOrDefault(lambda p: p.providerName == name)
            return provider

    async def testProvider(self, dto: TestRequestDto) -> ProviderTestResponse:
       
        result = await self._executeProviderTest(dto)

        try:
            async with self.uow:
                session = self.uow.session  # type: ignore[attr-defined]
                await session.execute(
                    sqlUpdate(ProviderModel)
                    .where(
                        ProviderModel.providerName == dto.providerName,
                        ProviderModel.channel == dto.channel,
                    )
                    .values(lastTestedAt=datetime.utcnow(), lastTestSuccess=result.success)
                )
        except Exception:
            # A failure to record test history should never mask the test
            # result itself reaching the caller - log and move on.
            logger.exception(
                "Failed to persist provider test result for %s/%s", dto.channel, dto.providerName
            )

        return result

    async def _executeProviderTest(self, dto: TestRequestDto) -> ProviderTestResponse:
        # Implement the logic to test the provider with the given configuration
        match dto.channel:
            case "sms":
                # Add SMS provider testing logic here
                match dto.providerName:
                    case "kifiya":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.kifiyaSmsProvider.test(provider_config, dto.address)
                    case "afromessage":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.afromessageSmsProvider.test(provider_config, dto.address)
                    case "jasmin":
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.jasminSmsProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.providerName}")
            case "inapp":
                match dto.providerName:
                    case "fcm":
                        # Extract nested config if it exists, otherwise use config directly
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.fcmProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.providerName}")
            
            case "email":
                match dto.providerName:
                    case "smtp":
                        # Extract nested config if it exists, otherwise use config directly
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.smtpProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.providerName}")
                        
            case "telegram":
                match dto.providerName:
                    case "telegram":
                        if not self.telegramProvider:
                            raise ValueError("TelegramProvider is not initialized")
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.telegramProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.providerName}")
            #new
            case "whatsapp":
                match dto.providerName:
                    case "meta_cloud":
                        # Extract nested config if it exists, otherwise use config directly
                        provider_config = dto.config.get("config", dto.config) if isinstance(dto.config, dict) else dto.config
                        return await self.metaCloudProvider.test(provider_config, dto.address)
                    case _:
                        raise ValueError(f"Unsupported provider: {dto.providerName}")
            #new
                
            case _:
                raise ValueError(f"Unsupported channel: {dto.channel}")
            