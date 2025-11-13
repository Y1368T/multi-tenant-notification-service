from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
import logging
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantFilterDTO
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.adapters.inbound.dto.sms_template_request_dto import (
    SMSTemplateRequestDTO,
    SMSTemplateResponseDTO,
    SMSTemplateFilterDTO
)
from notification_service.adapters.inbound.rest.routers.base_crud_router import BaseCRUDRouter
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, RelatedFilter
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ApplicationException, ValidationError
from qena_shared_lib.http import api_controller, get, post, put, patch, delete

logger = logging.getLogger(__name__)

@api_controller(prefix="/sms-templates", tags=["SMS Templates"])
class SMSTemplateController(BaseCRUDRouter[SmsTemplate, SMSTemplateFilterDTO, SMSTemplateResponseDTO, SMSTemplateService, SMSTemplateRequestDTO, SMSTemplateRequestDTO]):
    
    def __init__(self, smsTemplateService: SMSTemplateService = Depends()):
        super().__init__(
            service=smsTemplateService,
            prefix="/sms-templates",
            tags=["SMS Templates"],
            request_dto_class=SMSTemplateFilterDTO,
            response_dto_class=SMSTemplateResponseDTO,
            entity_class=SmsTemplate,
            create_dto_class=SMSTemplateRequestDTO,
            update_dto_class=SMSTemplateRequestDTO
        )
    
    @get("/get", response_model=PaginatedResponseDTO[SMSTemplateResponseDTO])
    async def get(self, params: SMSTemplateFilterDTO = Depends())->PaginatedResponseDTO[SMSTemplateResponseDTO]:
        """Get SMS templates by filters."""
        try:
           
            # Convert DTO to PaginatedRequest using service's methods
            paginated_request = self._build_paginated_request(params)
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    
    def _build_paginated_request(self, params: SMSTemplateFilterDTO) -> PaginatedRequest:
        """
        Build PaginatedRequest with searchFields, relatedFilters, and filters.
        Override this method to provide entity-specific search fields and related filters.
        """
        # Build root filters (including custom filters)
        root_filters = {}
        if hasattr(params, 'id') and params.id:
                try:
                    from uuid import UUID
                    root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
                except (ValueError, AttributeError):
                    root_filters['id'] = params.id
            
        if hasattr(params, 'tenantId') and params.tenantId:
                try:
                    tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                    root_filters['tenantId'] = tenant_id_value
                    logger.info(f"[DEBUG] Added tenantId to root_filters: {tenant_id_value} (type: {type(tenant_id_value)})")
                except (ValueError, AttributeError) as e:
                    root_filters['tenantId'] = params.tenantId
                    logger.warning(f"[DEBUG] Failed to convert tenantId to UUID: {e}, using raw value: {params.tenantId}")
        if hasattr(params, 'isActive') and params.isActive is not None:
                root_filters['isActive'] = params.isActive
        custom_filters = self.service._extract_custom_filters(params)
        root_filters.update(custom_filters)
            
        # Build related filters, but exclude tenant filter if we're already filtering by tenantId in root filters
        related_filters = self.service._build_related_filters(params)
        # Remove tenant-related filter if we're filtering by tenantId directly (more efficient)
        if 'tenantId' in root_filters:
            related_filters = [rf for rf in related_filters if not (rf.relationshipPath == "tenant" and rf.field == "id")]
        search_fields = ["templateName", "serviceName"]
        
        # Build and return PaginatedRequest
        paginated_request = PaginatedRequest(
                page=params.page,
                pageSize=params.pageSize,
                sortBy=params.sortBy or "createdAt",
                sortDirection=params.sortDirection,
                searchText=params.search,
                searchFields=search_fields,
                filters=root_filters,
                relatedFilters=related_filters
            )
        return paginated_request
    
    def _extract_custom_filters(self, params: SMSTemplateFilterDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'templateName') and params.templateName:
            filters["templateName"] = params.templateName
        if hasattr(params, 'serviceName') and params.serviceName:
            filters["serviceName"] = params.serviceName
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    
    @post("/create", response_model=SMSTemplateResponseDTO)
    async def create(self, request_dto: SMSTemplateRequestDTO) -> SMSTemplateResponseDTO:
        """
        Create a new SMS template.
        POST /sms-templates/create
        """
        try:
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            created_entity = await self.service.create(entity)
            
            # Convert entity to response DTO
            if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
                return SMSTemplateResponseDTO.fromEntityWithRelations(created_entity)
            else:
                return created_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @put("/{id}", response_model=SMSTemplateResponseDTO)
    async def update(self, id: UUID, request_dto: SMSTemplateRequestDTO) -> SMSTemplateResponseDTO:
        """
        Full update of an SMS template.
        PUT /sms-templates/{id}
        """
        try:
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
                entity.id = id
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            updated_entity = await self.service.update(entity)
            
            # Convert to response DTO
            if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
                return SMSTemplateResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @patch("/{id}", response_model=SMSTemplateResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> SMSTemplateResponseDTO:
        """
        Partial update of an SMS template.
        PATCH /sms-templates/{id}
        """
        try:
            # Call service
            updated_entity = await self.service.partial_update(id, updates)
            
            # Convert to response DTO
            if hasattr(SMSTemplateResponseDTO, 'fromEntityWithRelations'):
                return SMSTemplateResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete an SMS template.
        DELETE /sms-templates/{id}
        """
        try:
            await self.service.delete(id)
            return {"message": "SMS template deleted successfully"}
        except ApplicationException as e:
            raise self._handle_error(e)
    
    