from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.adapters.inbound.dto.sms_template_request_dto import SMSTemplateResponseDTO
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
from typing import List, Optional, Dict, Any
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService

class SMSTemplateService(BaseService[SmsTemplate, SMSTemplateResponseDTO]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, SmsTemplate, SMSTemplateResponseDTO)
        self.uow = uow
    
    def _get_repository(self):
        """Get SMS templates repository."""
        return self.uow.smsTemplates
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for SMS templates."""
        related_filters: List[RelatedFilter] = []
        if hasattr(params, 'tenantId') and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="tenant",
                    field="id",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                )
            )
        return related_filters
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for SMS templates."""
        return ["templateName", "serviceName"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for SMS templates."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
        if hasattr(params, 'tenantId') and params.tenantId:
            try:
                tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                root_filters['tenantId'] = tenant_id_value
            except (ValueError, AttributeError):
                root_filters['tenantId'] = params.tenantId
        
        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Build related filters, but exclude tenant filter if we're already filtering by tenantId in root filters
        related_filters = self._build_related_filters(params)
        # Remove tenant-related filter if we're filtering by tenantId directly (more efficient)
        if 'tenantId' in root_filters:
            related_filters = [rf for rf in related_filters if not (rf.relationshipPath == "tenant" and rf.field == "id")]
        
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
    
    # Keep old method for backward compatibility
    async def createSmsTemplate(self, template: SmsTemplate):
        """Create a new SMS template (deprecated - use create() instead)."""
        return await self.create(template)
        
    async def getSmsTemplateById(self, templateId):
        """Retrieve an SMS template by its ID.
        
        Args:
            templateId: UUID of the SMS template
            
        Returns:
            SmsTemplate entity if found, None otherwise
        """
        async with self.uow:
            template = await self.uow.smsTemplates.getById(templateId)
            return template
    
    # Keep old methods for backward compatibility
    async def updateSmsTemplate(self, template):
        """Update an existing SMS template (deprecated - use update() instead)."""
        return await self.update(template)
    
    async def deleteSmsTemplate(self, templateId):
        """Delete an SMS template (deprecated - use delete() instead)."""
        await self.delete(templateId)
    
    async def listSmsTemplatesByTenant(self, tenantId):
        """List all SMS templates for a given tenant.
        
        Args:
            tenantId: UUID of the tenant
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.smsTemplates.listByTenant(tenantId)
            return templates
    
    async def getTemplateByFilters(self,tenantId:UUID,templateName:str,serviceName:str):
        """ get list of templates by filters"""
        async with self.uow:
            templates=await self.uow.smsTemplates.list(lambda x:x.tenantId==tenantId and x.templateName==templateName and x.serviceName==serviceName)
            return templates
    
    async def getTemplatesByTenant(self, tenantId: UUID):
        """Retrieve SMS templates by tenant ID.
        
        Args:
            tenantId: UUID of the tenant
            
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.smsTemplates.list(lambda x: x.tenantId == tenantId)
            return templates
        
    # Keep old method for backward compatibility
    async def getAllTemplatesAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[SMSTemplateResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)