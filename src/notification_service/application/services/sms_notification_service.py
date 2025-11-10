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
from notification_service.domain.value_objects.paged_request import PagedRequest, SortDirection
from notification_service.adpaters.inbound.dto.sms_notification_response_dto import SMSNotificationResponseDTO
from notification_service.adpaters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from sqlalchemy.orm import joinedload, selectinload
from notification_service.Infrastructure.persisitence.models.sms.sms_notification import SMSNotificationModel
from notification_service.Infrastructure.persisitence.models.sms.sms_template import SmsTemplateModel
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
    
    async def get_sms_notifications(
        self, 
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None
    ) -> PaginatedResult[SMSNotification]:
        """
        Retrieve SMS notifications for a given tenant with pagination.
        
        Args:
            tenant_id: Tenant identifier
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Optional status filter ('pending', 'sent', 'failed', etc.)
            
        Returns:
            PaginatedResult containing SMSNotification entities and pagination metadata
        """
        async with self.uow:
            query = self.uow.sms_notifications\
                .query()\
                .include("template", "template.tenant")\
                .where(lambda x: x.template is not None)\
                .where(lambda x: x.template.tenant_id == tenant_id)
            
            if status:
                query = query.where(lambda x: x.status == status)
            
            result = await query\
                .order_by_descending(lambda x: x.created_at, "created_at")\
                .to_paginated_list(page=page, page_size=page_size)
            
            dto_items = [
                SMSNotificationResponseDTO.from_entity_with_relations(n)
                for n in result.items
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
    
    async def get_sms_notifications_simple(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None
    ) -> PaginatedResult[SMSNotification]:
        """
        Alternative: Using list_paginated with filters.
        More efficient for SQL-level filtering.
        """
        async with self.uow:
            filters = {}
            if status:
                filters['status'] = status
            
            # Note: This won't filter by template.tenant_id at SQL level
            # Use list_by_related_equal for join-based filtering
            result = await self.uow.sms_notifications.list_paginated(
                page=page,
                page_size=page_size,
                filters=filters,
                loader_options=[joinedload(SMSNotificationModel.template)],
                order_by=SMSNotificationModel.created_at.desc()
            )
            
            return result
        
    # ============================================================================
    # LINQ-Style Query Examples
    # ============================================================================
    
    async def get_notifications_linq_basic(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResult[SMSNotification]:
        """
        Example 1: Basic LINQ query with where, order by, and pagination.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId)
                .OrderByDescending(x => x.CreatedAt)
                .ToPagedListAsync(page, pageSize);
        """
        async with self.uow:
            result = await (
                self.uow.sms_notifications.query()
                .where(lambda x: x.template.tenant_id == tenant_id)
                .order_by_descending(lambda x: x.created_at, "created_at")
                .to_paginated_list(page, page_size)
            )
            return result
    
    async def get_notifications_by_status_and_prefix(
        self,
        tenant_id: UUID,
        prefix: str,
        status: NotificationStatus,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResult[SMSNotification]:
        """
        Example 2: Complex filtering with multiple conditions.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId && 
                           x.Template.Tenant.Prefix == prefix &&
                           x.Status == status)
                .OrderBy(x => x.Template.Name)
                .ThenByDescending(x => x.CreatedAt)
                .ToPagedListAsync(page, pageSize);
        """
        async with self.uow:
            result = await (
                self.uow.sms_notifications.query()
                .include("template", "template.tenant")  # Eager load relationships
                .where(lambda x: 
                    x.template.tenant_id == tenant_id and
                    x.template.tenant.prefix == prefix and
                    x.status == status
                )
                .order_by(lambda x: x.template.name, "template_id")
                .then_by_descending(lambda x: x.created_at, "created_at")
                .to_paginated_list(page, page_size)
            )
            return result
    
    async def get_recent_failed_notifications(
        self,
        tenant_id: UUID,
        limit: int = 10
    ) -> list[SMSNotification]:
        """
        Example 3: Get recent failed notifications without pagination.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId && 
                           x.Status == NotificationStatus.Failed)
                .OrderByDescending(x => x.CreatedAt)
                .Take(limit)
                .ToListAsync();
        """
        async with self.uow:
            results = await (
                self.uow.sms_notifications.query()
                .include("template")
                .where(lambda x: 
                    x.template.tenant_id == tenant_id and
                    x.status == NotificationStatus.FAILED
                )
                .order_by_descending(lambda x: x.created_at, "created_at")
                .take(limit)
                .to_list()
            )
            return results
    
    async def get_notification_by_id_linq(
        self,
        notification_id: UUID
    ) -> Optional[SMSNotification]:
        """
        Example 4: Get single notification by ID.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Id == notificationId)
                .Include(x => x.Template)
                .ThenInclude(x => x.Tenant)
                .FirstOrDefaultAsync();
        """
        async with self.uow:
            notification = await (
                self.uow.sms_notifications.query()
                .include("template", "template.tenant")
                .where(lambda x: x.id == notification_id)
                .first_or_default()
            )
            return notification
    
    async def get_notification_statistics(
        self,
        tenant_id: UUID
    ) -> dict:
        """
        Example 5: Aggregation queries - count, sum, average, etc.
        
        Equivalent .NET:
            var stats = new {
                TotalCount = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId)
                    .CountAsync(),
                FailedCount = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId && 
                               x.Status == NotificationStatus.Failed)
                    .CountAsync(),
                TotalRetries = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId)
                    .SumAsync(x => x.RetryCount),
                AverageRetries = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId)
                    .AverageAsync(x => x.RetryCount)
            };
        """
        async with self.uow:
            query = self.uow.sms_notifications.query().where(
                lambda x: x.template.tenant_id == tenant_id
            )
            
            total_count = await query.count()
            
            failed_query = self.uow.sms_notifications.query().where(
                lambda x: x.template.tenant_id == tenant_id and
                         x.status == NotificationStatus.FAILED
            )
            failed_count = await failed_query.count()
            
            total_retries = await query.sum(lambda x: x.retry_count)
            avg_retries = await query.average(lambda x: x.retry_count)
            
            return {
                "total_count": total_count,
                "failed_count": failed_count,
                "total_retries": total_retries,
                "average_retries": avg_retries
            }
    
    async def get_notifications_grouped_by_status(
        self,
        tenant_id: UUID
    ) -> dict[NotificationStatus, list[SMSNotification]]:
        """
        Example 6: Group by operation.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId)
                .GroupBy(x => x.Status)
                .ToListAsync();
        """
        async with self.uow:
            groups = await (
                self.uow.sms_notifications.query()
                .include("template")
                .where(lambda x: x.template.tenant_id == tenant_id)
                .group_by(lambda x: x.status)
            )
            return groups
    
    async def get_distinct_phone_numbers(
        self,
        tenant_id: UUID
    ) -> list[str]:
        """
        Example 7: Select distinct values.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId)
                .Select(x => x.RecipientPhone)
                .Distinct()
                .ToListAsync();
        """
        async with self.uow:
            phone_numbers = await (
                self.uow.sms_notifications.query()
                .where(lambda x: x.template.tenant_id == tenant_id)
                .select(lambda x: x.recipient_phone)
                .distinct()
            )
            return phone_numbers
    
    async def check_has_pending_notifications(
        self,
        tenant_id: UUID
    ) -> bool:
        """
        Example 8: Check if any records exist matching criteria.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .AnyAsync(x => x.Template.TenantId == tenantId && 
                              x.Status == NotificationStatus.Pending);
        """
        async with self.uow:
            has_pending = await (
                self.uow.sms_notifications.query()
                .where(lambda x: 
                    x.template.tenant_id == tenant_id and
                    x.status == NotificationStatus.PENDING
                )
                .any()
            )
            return has_pending
    
    async def get_notifications_with_projection(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResult[dict]:
        """
        Example 9: Select with projection to custom shape.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId)
                .Select(x => new {
                    Id = x.Id,
                    Phone = x.RecipientPhone,
                    Status = x.Status,
                    TemplateName = x.Template.Name,
                    CreatedAt = x.CreatedAt
                })
                .ToPagedListAsync(page, pageSize);
        """
        async with self.uow:
            result = await (
                self.uow.sms_notifications.query()
                .include("template")
                .where(lambda x: x.template.tenant_id == tenant_id)
                .select(lambda x: {
                    "id": x.id,
                    "phone": x.recipient_phone,
                    "status": x.status,
                    "template_name": x.template.name,
                    "created_at": x.created_at
                })
                .order_by_descending(lambda x: x["created_at"])
                .to_paginated_list(page, page_size)
            )
            return result
    
    async def get_notifications_with_skip_take(
        self,
        tenant_id: UUID,
        skip: int = 0,
        take: int = 10
    ) -> list[SMSNotification]:
        """
        Example 10: Manual pagination with Skip/Take.
        
        Equivalent .NET:
            await unitOfWork.SmsNotifications
                .Where(x => x.Template.TenantId == tenantId)
                .OrderBy(x => x.CreatedAt)
                .Skip(skip)
                .Take(take)
                .ToListAsync();
        """
        async with self.uow:
            results = await (
                self.uow.sms_notifications.query()
                .include("template")
                .where(lambda x: x.template.tenant_id == tenant_id)
                .order_by(lambda x: x.created_at, "created_at")
                .skip(skip)
                .take(take)
                .to_list()
            )
            return results
    
    async def get_oldest_and_newest_notification(
        self,
        tenant_id: UUID
    ) -> dict:
        """
        Example 11: Min/Max aggregations.
        
        Equivalent .NET:
            var stats = new {
                Oldest = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId)
                    .MinAsync(x => x.CreatedAt),
                Newest = await unitOfWork.SmsNotifications
                    .Where(x => x.Template.TenantId == tenantId)
                    .MaxAsync(x => x.CreatedAt)
            };
        """
        async with self.uow:
            query = self.uow.sms_notifications.query().where(
                lambda x: x.template.tenant_id == tenant_id
            )
            
            oldest = await query.min(lambda x: x.created_at)
            newest = await query.max(lambda x: x.created_at)
            
            return {
                "oldest": oldest,
                "newest": newest
            }
    
    async def get_all_notifications(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[UUID] = None
    ) -> PaginatedResponseDTO[SMSNotificationResponseDTO]:
        """
        Get all SMS notifications with pagination and filtering.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Search term for recipient number or message content
            status: Filter by notification status
            tenant_id: Filter by tenant ID
            
        Returns:
            PaginatedResponseDTO with enriched notification data
        """
        async with self.uow:
            # Use SQL-level filtering for tenant_id
            if tenant_id:
                result = await self.uow.sms_notifications.list_by_related_equal(
                    related_model=SmsTemplateModel,
                    relationship_name="template",
                    related_field="tenant_id",
                    value=tenant_id,
                    page=page,
                    page_size=page_size,
                    eager=True
                )
            else:
                # Get all notifications without tenant filter
                result = await self.uow.sms_notifications.find_paginated(
                  lambda t:t.template.tenant_id == tenant_id if tenant_id else True,
                  page=page,
                  page_size=page_size,
                  loader_options=[
                      selectinload(SMSNotificationModel.template).selectinload(SmsTemplateModel.tenant)
                  ],
                  order_by=SMSNotificationModel.created_at.desc()
                )
            
            # Apply additional in-memory filters if needed
            filtered_items = result.items
            
            if status:
                filtered_items = [n for n in filtered_items if n.status == status]
            
            if search:
                search_lower = search.lower()
                filtered_items = [
                    n for n in filtered_items
                    if (search_lower in (n.recipient_number or "").lower() or
                        search_lower in str(n.message_content or "").lower())
                ]
            
            # Recalculate pagination metadata if filters were applied
            if status or search:
                total_count = len(filtered_items)
                total_pages = (total_count + page_size - 1) // page_size
                # Apply pagination to filtered results
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                filtered_items = filtered_items[start_idx:end_idx]
            else:
                total_count = result.total_count
                total_pages = result.total_pages
            
            # Convert entities to DTOs
            dto_items = [
                SMSNotificationResponseDTO.from_entity_with_relations(notification)
                for notification in filtered_items
            ]
            
            # Return paginated response
            return PaginatedResponseDTO(
                items=dto_items,
                page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
    
    