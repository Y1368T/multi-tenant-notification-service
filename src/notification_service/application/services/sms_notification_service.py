from uuid import UUID
from typing import Optional, List, Dict, Any
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_types import NotificationChannel
import uuid

from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_response import BulkNotificationResponse, NotificationResponse
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.value_objects.paginated_result import PaginatedResult
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.application.services.base_service import BaseService
        
class SMSNotificationService(BaseService[SMSNotification, SMSNotificationResponseDTO]):
    def __init__(self, uow: IUnitOfWork, processMessageUseCase: ProcessMessageUseCase, messageRouter: IMessageHandler):
        super().__init__(uow, SMSNotification, SMSNotificationResponseDTO)
        self.uow = uow
        self.processMessageUseCase = processMessageUseCase
        self.messageRouter = messageRouter
    
    def _get_repository(self):
        """Get SMS notifications repository."""
        return self.uow.smsNotifications
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for SMS notifications."""
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
        """Get relationship paths to eager load for SMS notifications."""
        return ["template", "template.tenant"]
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for SMS notifications."""
        return ["recipientNumber", "template.templateName", "template.tenant.name", "template.tenant.prefix"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for SMS notifications."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
        # if hasattr(params, 'tenantId') and params.tenantId:
        #     try:
        #         tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
        #         root_filters['tenantId'] = tenant_id_value
        #     except (ValueError, AttributeError):
        #         root_filters['tenantId'] = params.tenantId
        
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

    async def prepareAndSendSms(
        self, 
        tenantId: UUID, 
        messageData: NotificationRequest
    ) -> NotificationResponse:
        """Prepare and send an SMS notification."""
        
        valid = self.processMessageUseCase.validateMessage(
            message=messageData,
            channel=NotificationChannel.SMS
        )
        
        if not valid.get("success"):
            return NotificationResponse(
                success=False,
                message=valid.get("error", "Validation failed")
            )
        
        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            
            if not tenant:
                return NotificationResponse(
                    success=False,
                    message="Tenant does not exist"
                )
            
            # REST API is always fire-and-forget mode:
            # - Failed messages go to outbox for automatic retry
            # - callbackUrl (if provided) is for async status updates, not mode selection
            # Immediate mode (isImmediateMode=True) is only for RabbitMQ RPC pattern
            isImmediateMode = False
            
            response = await self.messageRouter.doRoute(
                NotificationChannel.SMS, 
                tenant.prefix,  # Pass Tenant object
                messageData,
                isImmediateMode=isImmediateMode
            )
            return response

    async def prepareAndSendDirectSms(
        self,
        tenantId: UUID,
        messageData: DirectNotificationRequest,
    ) -> NotificationResponse:
        """Send an SMS without a pre-defined template."""
        if not getattr(messageData, "recipient", None) or not messageData.recipient.address:
            return NotificationResponse(success=False, message="recipient is required")
        recipient = messageData.recipient
        if not isinstance(recipient.address, str) or not recipient.address:
            return NotificationResponse(success=False, message="recipient must have a valid address")
        if not self.processMessageUseCase.isValidPhoneNumber(recipient.address):
            return NotificationResponse(success=False, message=f"Invalid phone number: {recipient.address}")
        if not messageData.message or not messageData.message.strip():
            return NotificationResponse(success=False, message="message is required")
        if not messageData.idempotencyKey:
            return NotificationResponse(success=False, message="idempotencyKey is required")

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                return NotificationResponse(success=False, message="Tenant does not exist")

            return await self.messageRouter.doDirectRoute(
                NotificationChannel.SMS, tenant.prefix, messageData, isImmediateMode=False
            )
    
    async def sendBulkSms(
        self, tenantId: UUID, notifications: List[NotificationRequest]
    ) -> BulkNotificationResponse:
        """Send multiple independent SMS notifications in one call.

        Each item carries its own recipient(s), payload, and idempotency key so
        content can be fully recipient-specific. Failures on individual items are
        collected and reported; valid items are still processed (partial success).
        """
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
            recipient_addr = (
                notification.recipient.address if getattr(notification, "recipient", None) else "unknown"
            )
            try:
                result = await self.prepareAndSendSms(tenantId, notification)
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
            notification = await self.uow.smsNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("SMSNotification", str(notificationId))
            return notification.status
    
    async def updateNotificationStatus(self, notificationId: UUID, status: str) -> SMSNotification:
        """Update notification status."""
        async with self.uow:
            notification = await self.uow.smsNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("SMSNotification", str(notificationId))
            notification.status = status
            updated = await self.uow.smsNotifications.update(notification)
            await self.uow.commit()
            return updated
    
    async def deleteNotification(self, notificationId: UUID):
        """Delete notification by ID."""
        await self.delete(notificationId)
    
    # Keep old method for backward compatibility
    async def getAllNotificationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)
    
    