from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.adapters.inbound.dto.sms_outbox_response_dto import SMSOutboxResponseDTO
from notification_service.adapters.inbound.dto.sms_outbox_filter_dto import SMSOutboxFilterDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from sqlalchemy.orm import selectinload
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel

class SMSOutboxService(BaseService[SMSOutbox, SMSOutboxResponseDTO]):
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, SMSOutbox, SMSOutboxResponseDTO)
        self.uow = uow
    
    def _get_repository(self):
        """Get SMS outbox repository."""
        return self.uow.smsOutboxes
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        if hasattr(params, 'recipientNumber') and params.recipientNumber:
            filters["recipientNumber"] = params.recipientNumber
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for SMS outbox."""
        related_filters: List[RelatedFilter] = []
        
        # Filter by tenantId through template
        if hasattr(params, 'tenantId') and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                )
            )
        
        # Filter by templateName
        if hasattr(params, 'templateName') and params.templateName:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="templateName",
                    op=FilterOp.EQ,
                    value=params.templateName
                )
            )
        
        # Filter by serviceName
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
        """Get relationship paths to eager load for SMS outbox."""
        return ["template", "template.tenant"]
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for SMS outbox."""
        return ["recipientNumber", "template.templateName", "template.serviceName", "template.tenant.name"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for SMS outbox."""
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
        
        # Get includes
        includes = self._get_includes()
        
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
            includes=includes
        )
    
    async def retry(self, outbox_id: UUID) -> SMSOutboxResponseDTO:
        """Retry a failed SMS outbox message.
        
        Args:
            outbox_id: UUID of the outbox message to retry
            
        Returns:
            SMSOutboxResponseDTO with updated retry information
            
        Raises:
            EntityNotFoundError: If outbox message not found
        """
        async with self.uow:
            # Get the outbox entity
            outbox = await self.uow.smsOutboxes.getById(outbox_id)
            if not outbox:
                raise EntityNotFoundError(f"SMS outbox with id {outbox_id} not found")
            
            # Reset retry information for manual retry
            outbox.retryCount = 0
            outbox.lastRetryAt = None
            outbox.lastErrorMessage = None
            outbox.nextRetryAt = None
            outbox.status = "pending"
            outbox.updatedAt = datetime.utcnow()
            
            # Update the outbox
            updated_outbox = await self.uow.smsOutboxes.update(outbox)
            await self.uow.commit()
            
            # Reload with relationships for response
            from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
            
            loader_options = [
                selectinload(SmsOutboxModel.template).selectinload(SmsTemplateModel.tenant)
            ]
            updated_outbox = await self.uow.smsOutboxes.getById(outbox_id, loader_options=loader_options)
            
            return SMSOutboxResponseDTO.fromEntityWithRelations(updated_outbox)
