from uuid import UUID
from typing import Optional, List, Dict, Any
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.telegram.telegram_notification import TelegramNotification
from notification_service.domain.value_objects.notification_types import NotificationChannel
import uuid

from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_response import BulkNotificationResponse, NotificationResponse
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.telegram_notification_response_dto import TelegramNotificationResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.application.services.base_service import BaseService
import logging

logger = logging.getLogger(__name__)


class TelegramNotificationService(BaseService[TelegramNotification, TelegramNotificationResponseDTO]):
    """Application service for sending and managing Telegram notifications.

    Delegates actual delivery to ``TelegramChannelHandler`` via the message
    router, following the same fire-and-forget pattern used for SMS/Email.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        processMessageUseCase: ProcessMessageUseCase,
        messageRouter: IMessageHandler
    ):
        super().__init__(uow, TelegramNotification, TelegramNotificationResponseDTO)
        self.uow = uow
        self.processMessageUseCase = processMessageUseCase
        self.messageRouter = messageRouter

    def _get_repository(self):
        return self.uow.telegramNotifications

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
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
        return related_filters

    def _get_includes(self) -> List[str]:
        return ["template", "template.tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        return ["recipientChatId", "template.templateName", "template.tenant.name", "template.tenant.prefix"]

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
            relatedFilters=self._build_related_filters(params)
        )

    async def prepareAndSendTelegram(
        self,
        tenantId: UUID,
        messageData: NotificationRequest
    ) -> NotificationResponse:
        """Validate and dispatch a Telegram notification through the message router."""
        valid = self.processMessageUseCase.validateMessage(
            message=messageData,
            channel=NotificationChannel.TELEGRAM
        )

        if not valid.get("success"):
            return NotificationResponse(
                success=False,
                message=valid.get("error", "Validation failed")
            )

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                return NotificationResponse(success=False, message="Tenant does not exist")

            return await self.messageRouter.doRoute(
                NotificationChannel.TELEGRAM,
                tenant.prefix,
                messageData,
                isImmediateMode=False
            )

    async def sendBulkTelegram(
        self, tenantId: UUID, notifications: List[NotificationRequest]
    ) -> BulkNotificationResponse:
        """Send multiple independent Telegram notifications in one call."""
        batch_id = str(uuid.uuid4())

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                failures = [
                    {
                        "recipient": n.recipient.address if getattr(n, "recipient", None) else "unknown",
                        "reason": "Tenant does not exist",
                    }
                    for n in notifications
                ]
                return BulkNotificationResponse(
                    batchId=batch_id,
                    totalSubmitted=len(notifications),
                    successfulSubmissions=0,
                    failedSubmissions=len(notifications),
                    notificationIds=[],
                    failures=failures,
                    success=False,
                    message="Tenant does not exist",
                )

        notification_ids: List[str] = []
        failures: List[Dict[str, Any]] = []

        for notification in notifications:
            recipient_addr = notification.recipient.address if getattr(notification, "recipient", None) else "unknown"
            try:
                result = await self.prepareAndSendTelegram(tenantId, notification)
                if result.success:
                    if result.recipientResponse:
                        for rr in result.recipientResponse:
                            if rr.notificationId:
                                notification_ids.append(rr.notificationId)
                else:
                    failures.append({"recipient": recipient_addr, "reason": result.message or "Send failed"})
            except Exception as exc:
                failures.append({"recipient": recipient_addr, "reason": str(exc)})

        successful = len(notifications) - len(failures)
        return BulkNotificationResponse(
            batchId=batch_id,
            totalSubmitted=len(notifications),
            successfulSubmissions=successful,
            failedSubmissions=len(failures),
            notificationIds=notification_ids,
            failures=failures,
            success=len(failures) == 0,
        )

    async def getNotificationStatus(self, notificationId: UUID) -> str:
        """Get notification status by ID."""
        async with self.uow:
            notification = await self.uow.telegramNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("TelegramNotification", str(notificationId))
            return notification.status
