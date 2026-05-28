"""Email notification service following the same pattern as SMSNotificationService."""
from uuid import UUID
from typing import Optional, List, Dict, Any

import uuid

from notification_service.application.services.base_service import BaseService
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_response import BulkNotificationResponse, NotificationResponse
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.adapters.inbound.dto.email_notification_response_dto import EmailNotificationResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp,
)


class EmailNotificationService(BaseService[EmailNotification, EmailNotificationResponseDTO]):
    """Service for managing email notifications."""

    def __init__(
        self,
        uow: IUnitOfWork,
        processMessageUseCase: ProcessMessageUseCase,
        messageRouter: IMessageHandler,
    ):
        super().__init__(uow, EmailNotification, EmailNotificationResponseDTO)
        self.uow = uow
        self.processMessageUseCase = processMessageUseCase
        self.messageRouter = messageRouter

    def _get_repository(self):
        """Get Email notifications repository."""
        return self.uow.emailNotifications

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, "status") and params.status:
            filters["status"] = params.status
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for Email notifications."""
        related_filters: List[RelatedFilter] = []
        if hasattr(params, "tenantId") and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId)
                    if isinstance(params.tenantId, str)
                    else params.tenantId,
                )
            )
        return related_filters

    def _get_includes(self) -> List[str]:
        """Get relationship paths to eager load for Email notifications."""
        return ["template", "template.tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for Email notifications."""
        return [
            "recipientEmail",
            "template.templateName",
            "template.tenant.name",
            "template.tenant.prefix",
        ]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for Email notifications."""
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
        )

    async def prepareAndSendEmail(
        self, tenantId: UUID, messageData: NotificationRequest
    ) -> NotificationResponse:
        """Prepare and send an Email notification."""
        valid = self.processMessageUseCase.validateMessage(
            message=messageData, channel=NotificationChannel.EMAIL
        )

        if not valid.get("success"):
            return NotificationResponse(
                success=False, message=valid.get("error", "Validation failed")
            )

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)

            if not tenant:
                return NotificationResponse(success=False, message="Tenant does not exist")

            # REST API is always fire-and-forget mode:
            # - Failed messages go to outbox for automatic retry
            # - callbackUrl (if provided) is for async status updates, not mode selection
            # Immediate mode (isImmediateMode=True) is only for RabbitMQ RPC pattern
            isImmediateMode = False
            
            response = await self.messageRouter.doRoute(
                NotificationChannel.EMAIL, tenant.prefix, messageData,
                isImmediateMode=isImmediateMode
            )
            return response

    async def prepareAndSendDirectEmail(
        self,
        tenantId: UUID,
        messageData: DirectNotificationRequest,
    ) -> NotificationResponse:
        """Send an email without a pre-defined template."""
        if not messageData.recipients:
            return NotificationResponse(success=False, message="At least one recipient is required")
        for recipient in messageData.recipients:
            if not isinstance(recipient.address, str) or not recipient.address:
                return NotificationResponse(success=False, message="Each recipient must have a valid address")
            if not self.processMessageUseCase.isValidEmail(recipient.address):
                return NotificationResponse(success=False, message=f"Invalid email address: {recipient.address}")
        if not messageData.message or not messageData.message.strip():
            return NotificationResponse(success=False, message="message is required")
        if not messageData.subject or not messageData.subject.strip():
            return NotificationResponse(success=False, message="subject is required for email")
        if not messageData.idempotencyKey:
            return NotificationResponse(success=False, message="idempotencyKey is required")

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                return NotificationResponse(success=False, message="Tenant does not exist")

            return await self.messageRouter.doDirectRoute(
                NotificationChannel.EMAIL, tenant.prefix, messageData, isImmediateMode=False
            )

    async def sendBulkEmail(
        self, tenantId: UUID, notifications: List[NotificationRequest]
    ) -> BulkNotificationResponse:
        """Send multiple independent email notifications in one call.

        Each item carries its own recipient(s), payload, and idempotency key so
        content can be fully recipient-specific. Processing is sequential so each
        item manages its own Unit-of-Work transaction safely. Failures on
        individual items are collected and reported in the response; valid items
        are still processed (partial success).
        """
        batch_id = str(uuid.uuid4())

        # Fail-fast: validate tenant once before processing any items.
        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                failures = [
                    {
                        "recipient": n.recipients[0].address if n.recipients else "unknown",
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
            recipient_addr = (
                notification.recipients[0].address if notification.recipients else "unknown"
            )
            try:
                result = await self.prepareAndSendEmail(tenantId, notification)
                if result.success:
                    if result.recipientResponse:
                        for rr in result.recipientResponse:
                            if rr.notificationId:
                                notification_ids.append(rr.notificationId)
                else:
                    failures.append(
                        {
                            "recipient": recipient_addr,
                            "reason": result.errorMessage or result.message or "Send failed",
                        }
                    )
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
            notification = await self.uow.emailNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import (
                    EntityNotFoundError,
                )

                raise EntityNotFoundError("EmailNotification", str(notificationId))
            return notification.status

    async def updateNotificationStatus(
        self, notificationId: UUID, status: str
    ) -> EmailNotification:
        """Update notification status."""
        async with self.uow:
            notification = await self.uow.emailNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import (
                    EntityNotFoundError,
                )

                raise EntityNotFoundError("EmailNotification", str(notificationId))
            notification.status = status
            updated = await self.uow.emailNotifications.update(notification)
            await self.uow.commit()
            return updated

    async def deleteNotification(self, notificationId: UUID):
        """Delete notification by ID."""
        await self.delete(notificationId)

    async def getAllNotificationsAdvanced(
        self, req: PaginatedRequest
    ) -> PaginatedResponseDTO[EmailNotificationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)
