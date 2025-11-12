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
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
class SMSNotificationService:
    def __init__(self, uow:IUnitOfWork, processMessageUseCase: ProcessMessageUseCase,messageRouter:IMessageHandler):
        self.uow = uow
        self.processMessageUseCase = processMessageUseCase
        self.messageRouter=messageRouter


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
            
            response = await self.messageRouter.doRoute(
                NotificationChannel.SMS, 
                tenant,  # Pass Tenant object
                messageData
            )
            return response
    
    async def getAllNotificationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        """
        async with self.uow:
            
            relatedFiltersTuples = [
            (rf.relationshipPath, rf.field, rf.op.value if hasattr(rf.op, 'value') else str(rf.op), rf.value)
            for rf in (req.relatedFilters or [])
            ]
            result = await self.uow.smsNotifications.listAdvancedPaginated(
                page=req.page,
                pageSize=req.pageSize,
                rootFilters=req.filters or {},
                relatedFilters=relatedFiltersTuples,
                includes=[],
                sortBy=req.sortBy,
                sortDirection=req.sortDirection.value,
                searchText=req.searchText,
                searchFields=req.searchFields or []
            )

            dtoItems = [
                SMSNotificationResponseDTO.fromEntityWithRelations(notification)
                for notification in result.items
            ]

            return PaginatedResponseDTO(
                items=dtoItems,
                page=result.page,
                pageSize=result.pageSize,
                totalCount=result.totalCount,
                totalPages=result.totalPages,
                hasNext=result.hasNext,
                hasPrevious=result.hasPrevious
            )
    
    