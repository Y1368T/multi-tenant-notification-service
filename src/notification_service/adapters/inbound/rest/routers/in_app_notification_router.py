from qena_shared_lib.http import ControllerBase, get, post, api_controller, put, delete, patch
from notification_service.application.services.in_app_notification_service import InAppNotificationService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.in_app_notification_response_dto import InAppNotificationResponseDTO
from notification_service.adapters.inbound.dto.in_app_notification_request_dto import InAppNotificationFilterDTO
from notification_service.adapters.inbound.dto.bulk_notification_request_dto import BulkNotificationRequestDTO
from typing import Dict, Any, List, Optional
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    RelatedFilter,
    FilterOp
)
from uuid import UUID
from fastapi import Depends, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class MarkReadRequest(BaseModel):
    """Request body for marking notifications as read."""
    notificationIds: Optional[List[UUID]] = None  # If None, mark all as read


class ClearNotificationsRequest(BaseModel):
    """Request body for clearing notifications."""
    notificationIds: Optional[List[UUID]] = None  # If None, clear all


# We have stopped using basecrudrouter because InAppNotification can't be updated and created using a rest request
# so we are using controllerbase instead of basecrudrouter and this controller will only have get and send endpoints 

@api_controller(prefix="/in-app-notifications", tags=["In-App Notifications"])
class InAppNotificationController(ControllerBase):
    
    def __init__(self, inAppNotificationService: InAppNotificationService = Depends()):
        self.inAppNotificationService = inAppNotificationService
        
    
    
    @get("/getAll", response_model=PaginatedResponseDTO[InAppNotificationResponseDTO])
    async def getAll(self, params: InAppNotificationFilterDTO = Depends()) -> PaginatedResponseDTO[InAppNotificationResponseDTO]:
        """Get in-app notifications by filters."""
        # Build PaginatedRequest using service method
        # Exceptions will be handled by global exception handlers
        paginated_request = self.inAppNotificationService._build_paginated_request(params)
        result = await self.inAppNotificationService.get(paginated_request)
        return result
    
    @get("/by-external-id/{external_id}", response_model=PaginatedResponseDTO[InAppNotificationResponseDTO])
    async def getByExternalId(
        self, 
        external_id: str,
        tenant_id: UUID = Query(..., description="Tenant ID to filter notifications"),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100),
        isRead: Optional[bool] = Query(None, description="Filter by read status")
    ) -> PaginatedResponseDTO[InAppNotificationResponseDTO]:
        """
        Get notifications for a user by their external ID (user ID in tenant's system).
        
        This endpoint allows tenant applications to fetch notifications for their users
        to display on the user's notification page.
        
        Args:
            external_id: The user ID in the tenant's system
            tenant_id: The tenant ID to filter notifications
            page: Page number (default: 1)
            pageSize: Number of items per page (default: 20)
            isRead: Optional filter for read/unread notifications
        """
        result = await self.inAppNotificationService.getByExternalId(
            externalId=external_id,
            tenantId=tenant_id,
            page=page,
            pageSize=pageSize,
            isRead=isRead
        )
        return result
    
    @get("/by-external-id/{external_id}/unread-count")
    async def getUnreadCount(
        self, 
        external_id: str,
        tenant_id: UUID = Query(..., description="Tenant ID to filter notifications")
    ) -> Dict[str, Any]:
        """
        Get the count of unread notifications for a user by their external ID.
        
        Args:
            external_id: The user ID in the tenant's system
            tenant_id: The tenant ID to filter notifications
        """
        count = await self.inAppNotificationService.getUnreadCountByExternalId(
            externalId=external_id,
            tenantId=tenant_id
        )
        return {"externalId": external_id, "unreadCount": count}
    
    @patch("/by-external-id/{external_id}/mark-read")
    async def markAsRead(
        self, 
        external_id: str,
        tenant_id: UUID = Query(..., description="Tenant ID"),
        request: Optional[MarkReadRequest] = None
    ) -> Dict[str, Any]:
        """
        Mark notifications as read for a user by their external ID.
        
        If notificationIds is provided, only those notifications are marked as read.
        If notificationIds is None or empty, all notifications for the user are marked as read.
        
        Args:
            external_id: The user ID in the tenant's system
            tenant_id: The tenant ID
            request: Optional request body with specific notification IDs to mark as read
        """
        notification_ids = request.notificationIds if request else None
        updated_count = await self.inAppNotificationService.markAsReadByExternalId(
            externalId=external_id,
            tenantId=tenant_id,
            notificationIds=notification_ids
        )
        return {
            "externalId": external_id, 
            "markedAsRead": updated_count,
            "message": f"Successfully marked {updated_count} notification(s) as read"
        }
    
    @patch("/{notification_id}/mark-read")
    async def markSingleAsRead(self, notification_id: UUID) -> Dict[str, Any]:
        """Mark a single notification as read by its ID."""
        await self.inAppNotificationService.markAsReadById(notification_id)
        return {"notificationId": str(notification_id), "isRead": True}
    
    @delete("/by-external-id/{external_id}/clear")
    async def clearNotifications(
        self, 
        external_id: str,
        tenant_id: UUID = Query(..., description="Tenant ID"),
        request: Optional[ClearNotificationsRequest] = None
    ) -> Dict[str, Any]:
        """
        Clear (delete) notifications for a user by their external ID.
        
        If notificationIds is provided, only those notifications are deleted.
        If notificationIds is None or empty, all notifications for the user are deleted.
        
        Args:
            external_id: The user ID in the tenant's system
            tenant_id: The tenant ID
            request: Optional request body with specific notification IDs to delete
        """
        notification_ids = request.notificationIds if request else None
        deleted_count = await self.inAppNotificationService.clearByExternalId(
            externalId=external_id,
            tenantId=tenant_id,
            notificationIds=notification_ids
        )
        return {
            "externalId": external_id, 
            "deletedCount": deleted_count,
            "message": f"Successfully deleted {deleted_count} notification(s)"
        }
   
    
    # Custom endpoints (not standard CRUD)
    @post("/send")
    async def send(self, tenant_id: UUID, requestDto: NotificationRequest):
        """Send in-app notification (custom endpoint)."""
        result = await self.inAppNotificationService.prepareAndSendInApp(tenant_id, requestDto)
        return result

    @post("/send-bulk")
    async def sendBulk(self, tenant_id: UUID, requestDto: BulkNotificationRequestDTO):
        """Send multiple recipient-specific in-app notifications in a single call.

        Each item in ``notifications`` is an independent notification with its
        own recipient, payload, and idempotency key. Valid items are processed
        even when others fail (partial success).
        """
        result = await self.inAppNotificationService.sendBulkInApp(
            tenant_id, requestDto.notifications
        )
        return result

