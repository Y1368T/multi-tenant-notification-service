from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
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
from notification_service.adapters.inbound.dto.in_app_notification_response_dto import InAppNotificationResponseDTO
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
        
class InAppNotificationService(BaseService[InAppNotification, InAppNotificationResponseDTO]):
    def __init__(self, uow: IUnitOfWork, processMessageUseCase: ProcessMessageUseCase, messageRouter: IMessageHandler):
        super().__init__(uow, InAppNotification, InAppNotificationResponseDTO)
        self.uow = uow
        self.processMessageUseCase = processMessageUseCase
        self.messageRouter = messageRouter
    
    def _get_repository(self):
        """Get in-app notifications repository."""
        return self.uow.inAppNotifications
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        if hasattr(params, 'externalId') and params.externalId:
            filters["externalId"] = params.externalId
        if hasattr(params, 'isRead') and params.isRead is not None:
            filters["isRead"] = params.isRead
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for in-app notifications."""
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
        """Get relationship paths to eager load for in-app notifications."""
        return ["template", "template.tenant"]
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for in-app notifications."""
        return ["recipientUserId", "externalId", "template.templateName", "template.tenant.name", "template.tenant.prefix"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for in-app notifications."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
        # Note: tenantId is NOT a direct column on InAppNotification
        # It's handled via related filters through the template relationship
        # See _build_related_filters() method
        
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

    async def prepareAndSendInApp(
        self, 
        tenantId: UUID, 
        messageData: NotificationRequest
    ) -> NotificationResponse:
        """Prepare and send an in-app notification."""
        
        valid = self.processMessageUseCase.validateMessage(
            message=messageData,
            channel=NotificationChannel.INAPP
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
                NotificationChannel.INAPP, 
                tenant.prefix,  # Pass Tenant object
                messageData,
                isImmediateMode=isImmediateMode
            )
            return response

    async def prepareAndSendDirectInApp(
        self,
        tenantId: UUID,
        messageData: DirectNotificationRequest,
    ) -> NotificationResponse:
        """Send an in-app notification without a pre-defined template."""
        if not getattr(messageData, "recipient", None) or not messageData.recipient.address:
            return NotificationResponse(success=False, message="recipient is required")
        recipient = messageData.recipient
        if not isinstance(recipient.address, str) or not recipient.address:
            return NotificationResponse(success=False, message="recipient must have a valid address")
        if not messageData.message or not messageData.message.strip():
            return NotificationResponse(success=False, message="message is required")
        if not messageData.title or not messageData.title.strip():
            return NotificationResponse(success=False, message="title is required for in-app notifications")
        if not messageData.idempotencyKey:
            return NotificationResponse(success=False, message="idempotencyKey is required")

        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            if not tenant:
                return NotificationResponse(success=False, message="Tenant does not exist")

            return await self.messageRouter.doDirectRoute(
                NotificationChannel.INAPP, tenant.prefix, messageData, isImmediateMode=False
            )
    
    async def sendBulkInApp(
        self, tenantId: UUID, notifications: List[NotificationRequest]
    ) -> BulkNotificationResponse:
        """Send multiple independent in-app notifications in one call.

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
                result = await self.prepareAndSendInApp(tenantId, notification)
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
            notification = await self.uow.inAppNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("InAppNotification", str(notificationId))
            return notification.status
    
    async def updateNotificationStatus(self, notificationId: UUID, status: str) -> InAppNotification:
        """Update notification status."""
        async with self.uow:
            notification = await self.uow.inAppNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("InAppNotification", str(notificationId))
            notification.status = status
            updated = await self.uow.inAppNotifications.update(notification)
            await self.uow.commit()
            return updated
    
    async def deleteNotification(self, notificationId: UUID):
        """Delete notification by ID."""
        await self.delete(notificationId)
    
    # Keep old method for backward compatibility
    async def getAllNotificationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[InAppNotificationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)
    
    # =========================================================================
    # External ID based methods for tenant applications
    # =========================================================================
    
    async def getByExternalId(
        self,
        externalId: str,
        tenantId: UUID,
        page: int = 1,
        pageSize: int = 20,
        isRead: Optional[bool] = None
    ) -> PaginatedResponseDTO[InAppNotificationResponseDTO]:
        """
        Get notifications for a user by their external ID.
        
        Args:
            externalId: User ID in tenant's system
            tenantId: Tenant ID to filter notifications
            page: Page number
            pageSize: Items per page
            isRead: Optional filter for read/unread status
            
        Returns:
            Paginated list of notifications
        """
        logger.info(f"Getting notifications for externalId={externalId}, tenantId={tenantId}")
        
        # Build filters
        filters = {"externalId": externalId}
        if isRead is not None:
            filters["isRead"] = isRead
        
        # Build related filter for tenant
        related_filters = [
            RelatedFilter(
                relationshipPath="template",
                field="tenantId",
                op=FilterOp.EQ,
                value=tenantId
            )
        ]
        
        paginated_request = PaginatedRequest(
            page=page,
            pageSize=pageSize,
            sortBy="createdAt",
            sortDirection="desc",
            filters=filters,
            relatedFilters=related_filters
        )
        
        return await self.get(paginated_request)
    
    async def getUnreadCountByExternalId(
        self,
        externalId: str,
        tenantId: UUID
    ) -> int:
        """
        Get count of unread notifications for a user by their external ID.
        
        Args:
            externalId: User ID in tenant's system
            tenantId: Tenant ID to filter notifications
            
        Returns:
            Count of unread notifications
        """
        logger.info(f"Getting unread count for externalId={externalId}, tenantId={tenantId}")
        
        async with self.uow:
            # Query notifications with externalId and isRead=False
            notifications = await self.uow.inAppNotifications.find(
                lambda n: n.externalId == externalId and n.isRead == False
            )
            
            # Filter by tenant through template relationship
            count = 0
            for notif in notifications:
                if notif.templateId:
                    template = await self.uow.inAppTemplates.getById(notif.templateId)
                    if template and template.tenantId == tenantId:
                        count += 1
            
            return count
    
    async def markAsReadByExternalId(
        self,
        externalId: str,
        tenantId: UUID,
        notificationIds: Optional[List[UUID]] = None
    ) -> int:
        """
        Mark notifications as read for a user by their external ID.
        
        Args:
            externalId: User ID in tenant's system
            tenantId: Tenant ID
            notificationIds: Optional list of specific notification IDs to mark as read.
                           If None, all notifications for the user are marked as read.
            
        Returns:
            Number of notifications marked as read
        """
        logger.info(f"Marking notifications as read for externalId={externalId}, tenantId={tenantId}")
        
        async with self.uow:
            # Get notifications by externalId
            if notificationIds:
                # Mark specific notifications
                notifications = await self.uow.inAppNotifications.find(
                    lambda n: n.externalId == externalId and n.id in notificationIds and n.isRead == False
                )
            else:
                # Mark all notifications for this user
                notifications = await self.uow.inAppNotifications.find(
                    lambda n: n.externalId == externalId and n.isRead == False
                )
            
            updated_count = 0
            for notif in notifications:
                # Verify tenant ownership through template
                if notif.templateId:
                    template = await self.uow.inAppTemplates.getById(notif.templateId)
                    if template and template.tenantId == tenantId:
                        notif.isRead = True
                        notif.status = "read"
                        notif.updatedAt = datetime.utcnow()
                        await self.uow.inAppNotifications.update(notif)
                        updated_count += 1
            
            await self.uow.commit()
            logger.info(f"Marked {updated_count} notifications as read for externalId={externalId}")
            return updated_count
    
    async def markAsReadById(self, notificationId: UUID) -> None:
        """
        Mark a single notification as read by its ID.
        
        Args:
            notificationId: The notification ID
        """
        async with self.uow:
            notification = await self.uow.inAppNotifications.getById(notificationId)
            if not notification:
                from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
                raise EntityNotFoundError("InAppNotification", str(notificationId))
            
            notification.isRead = True
            notification.status = "read"
            notification.updatedAt = datetime.utcnow()
            await self.uow.inAppNotifications.update(notification)
            await self.uow.commit()
    
    async def clearByExternalId(
        self,
        externalId: str,
        tenantId: UUID,
        notificationIds: Optional[List[UUID]] = None
    ) -> int:
        """
        Clear (delete) notifications for a user by their external ID.
        
        Args:
            externalId: User ID in tenant's system
            tenantId: Tenant ID
            notificationIds: Optional list of specific notification IDs to delete.
                           If None, all notifications for the user are deleted.
            
        Returns:
            Number of notifications deleted
        """
        logger.info(f"Clearing notifications for externalId={externalId}, tenantId={tenantId}")
        
        async with self.uow:
            # Get notifications by externalId
            if notificationIds:
                notifications = await self.uow.inAppNotifications.find(
                    lambda n: n.externalId == externalId and n.id in notificationIds
                )
            else:
                notifications = await self.uow.inAppNotifications.find(
                    lambda n: n.externalId == externalId
                )
            
            deleted_count = 0
            for notif in notifications:
                # Verify tenant ownership through template
                if notif.templateId:
                    template = await self.uow.inAppTemplates.getById(notif.templateId)
                    if template and template.tenantId == tenantId:
                        await self.uow.inAppNotifications.delete(notif.id)
                        deleted_count += 1
            
            await self.uow.commit()
            logger.info(f"Deleted {deleted_count} notifications for externalId={externalId}")
            return deleted_count

