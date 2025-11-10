from uuid import UUID
from typing import Optional
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.value_objects.paginated_result import PaginatedResult
from notification_service.adapters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from sqlalchemy.orm import joinedload, selectinload
from notification_service.infrastructure.persisitence.models.sms.sms_notification import SMSNotificationModel
from notification_service.infrastructure.persisitence.models.sms.sms_template import SmsTemplateModel
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
class SMSNotificationService:
    def __init__(self, uow:IUnitOfWork, process_message_use_case: ProcessMessageUseCase,message_router:IMessageHandler):
        self.uow = uow
        self.process_message_use_case = process_message_use_case
        self.message_router=message_router


    async def prepare_and_send_sms(
        self, 
        tenant_id: UUID, 
        message_data: NotificationRequest
    ) -> NotificationResponse:
        """Prepare and send an SMS notification."""
        
        valid = self.process_message_use_case.validate_message(
            message=message_data,
            channel=NotificationChannel.SMS
        )
        
        if not valid.get("success"):
            return NotificationResponse(
                success=False,
                message=valid.get("error", "Validation failed")
            )
        
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(tenant_id)
            
            if not tenant:
                return NotificationResponse(
                    success=False,
                    message="Tenant does not exist"
                )
            
            response = await self.message_router.do_route(
                NotificationChannel.SMS, 
                tenant,  # Pass Tenant object
                message_data
            )
            return response
    
    async def get_all_notifications_advanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        """
        async with self.uow:
            
            related_filters_tuples = [
            (rf.relationship_path, rf.field, rf.op.value if hasattr(rf.op, 'value') else str(rf.op), rf.value)
            for rf in (req.related_filters or [])
            ]
            result = await self.uow.sms_notifications.list_advanced_paginated(
                page=req.page,
                page_size=req.page_size,
                root_filters=req.filters or {},
                related_filters=related_filters_tuples,
                includes=[],
                sort_by=req.sort_by,
                sort_direction=req.sort_direction.value,
                search_text=req.search_text,
                search_fields=req.search_fields or []
            )

            dto_items = [
                SMSNotificationResponseDTO.from_entity_with_relations(notification)
                for notification in result.items
            ]

            return PaginatedResponseDTO(
                items=dto_items,
                page=result.page,
                page_size=result.page_size,
                total_count=result.total_count,
                total_pages=result.total_pages,
                has_next=result.has_next,
                has_previous=result.has_previous
            )
    
    