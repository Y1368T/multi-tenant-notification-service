from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.telegram.telegram_outbox import TelegramOutbox
from notification_service.adapters.inbound.dto.telegram_outbox_response_dto import TelegramOutboxResponseDTO
from notification_service.adapters.inbound.dto.telegram_outbox_filter_dto import TelegramOutboxFilterDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError, ValidationError
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.domain.entities.telegram.telegram_notification import TelegramNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.infrastructure.providers.telegram.telegram_provider import TelegramProvider
import logging

logger = logging.getLogger(__name__)


class TelegramOutboxService(BaseService[TelegramOutbox, TelegramOutboxResponseDTO]):
    """Application service for managing the Telegram outbox.

    The outbox acts as a durable retry queue. Failed Telegram deliveries are
    written here by ``TelegramChannelHandler`` and retried by the background
    ``OutboxProcessor``. The ``retry()`` method allows operators to force an
    immediate re-attempt via the REST API.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        telegramProvider: TelegramProvider,
    ):
        super().__init__(uow, TelegramOutbox, TelegramOutboxResponseDTO)
        self.uow = uow
        self.telegram_providers = {
            "telegram": telegramProvider,
        }

    def _get_repository(self):
        return self.uow.telegramOutboxes

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        if hasattr(params, 'recipientChatId') and params.recipientChatId:
            filters["recipientChatId"] = params.recipientChatId
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        related_filters: List[RelatedFilter] = []

        if hasattr(params, 'tenantId') and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                )
            )

        if hasattr(params, 'templateName') and params.templateName:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="templateName",
                    op=FilterOp.EQ,
                    value=params.templateName
                )
            )

        if hasattr(params, 'serviceName') and params.serviceName:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="serviceName",
                    op=FilterOp.EQ,
                    value=params.serviceName
                )
            )

        return related_filters

    def _get_includes(self) -> List[str]:
        return ["template", "template.tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        return ["recipientChatId", "template.templateName", "template.serviceName", "template.tenant.name"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id

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
            relatedFilters=self._build_related_filters(params),
            includes=self._get_includes()
        )

    async def retry(self, outbox_id: UUID) -> TelegramOutboxResponseDTO:
        """Force-retry a failed Telegram outbox message immediately.

        Looks up the provider configuration from the matching
        ``TenantTelegramConfiguration``, attempts the send, then either
        moves the record to ``telegramNotifications`` on success or increments
        the retry counter and persists the error message on failure.

        Args:
            outbox_id: UUID of the outbox entry to retry.

        Returns:
            Updated ``TelegramOutboxResponseDTO`` reflecting the new state.

        Raises:
            EntityNotFoundError: If the outbox entry does not exist.
            ValidationError: If no active Telegram configuration is found.
        """
        async with self.uow:
            outbox = await self.uow.telegramOutboxes.getById(outbox_id)
            if not outbox:
                raise EntityNotFoundError(f"Telegram outbox with id {outbox_id} not found")

            template = await self.uow.telegramTemplates.getById(outbox.templateId)
            if not template:
                raise ValidationError(f"Template {outbox.templateId} not found for outbox message")

            tenant_id = template.tenantId

            configs = await self.uow.tenantTelegramConfigurations.find(
                lambda c: c.tenantId == tenant_id and c.isActive
            )
            if not configs:
                raise ValidationError(f"No active Telegram configuration found for tenant {tenant_id}")

            config = min(configs, key=lambda c: c.priority)
            provider_name = (config.providerName or "").lower()

            provider = self.telegram_providers.get(provider_name)
            if not provider:
                raise ValidationError(f"Telegram provider '{provider_name}' not registered")

            outbox.retryCount += 1
            outbox.lastRetryAt = datetime.utcnow()
            outbox.updatedAt = datetime.utcnow()

            try:
                logger.info(f"Manual retry: sending Telegram outbox {outbox_id} to {outbox.recipientChatId} via {provider_name}")
                success, error_msg = await provider.send_raw(
                    recipient=outbox.recipientChatId,
                    message=outbox.messageContent,
                    tenantConfig=config
                )

                if success:
                    logger.info(f"Telegram outbox {outbox_id} sent successfully, moving to notifications")
                    notification = TelegramNotification(
                        id=uuid4(),
                        recipientChatId=outbox.recipientChatId,
                        messageContent={"text": outbox.messageContent},
                        templateId=outbox.templateId,
                        status=NotificationStatus.SENT,
                        idempotencyKey=outbox.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.uow.telegramNotifications.add(notification)
                    await self.uow.telegramOutboxes.delete(outbox.id)
                    await self.uow.commit()

                    outbox.status = NotificationStatus.SENT
                    outbox.isSent = True
                    outbox.sentAt = datetime.utcnow()
                    return TelegramOutboxResponseDTO.fromEntityWithRelations(outbox)
                else:
                    logger.warning(f"Telegram outbox {outbox_id} retry failed: {error_msg}")
                    outbox.lastErrorMessage = error_msg
                    outbox.status = NotificationStatus.FAILED
                    await self.uow.telegramOutboxes.update(outbox)
                    await self.uow.commit()
                    updated = await self.uow.telegramOutboxes.getById(outbox_id)
                    return TelegramOutboxResponseDTO.fromEntityWithRelations(updated)

            except Exception as e:
                error_message = f"{type(e).__name__}: {str(e) or 'Unknown error during send attempt'}"
                outbox.lastErrorMessage = error_message
                outbox.status = NotificationStatus.FAILED
                await self.uow.telegramOutboxes.update(outbox)
                await self.uow.commit()
                logger.error(f"Error during manual retry of Telegram outbox {outbox_id}: {e}", exc_info=True)
                updated = await self.uow.telegramOutboxes.getById(outbox_id)
                return TelegramOutboxResponseDTO.fromEntityWithRelations(updated)
