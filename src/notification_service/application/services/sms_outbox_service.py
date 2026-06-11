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
from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError, ValidationError
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from sqlalchemy.orm import selectinload
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.infrastructure.providers.sms.kifiyaSmsProvider import KifiyaSMSProvider
from notification_service.infrastructure.providers.sms.jasmin_sms_provider import JasminSMSProvider
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
import logging

logger = logging.getLogger(__name__)

class SMSOutboxService(BaseService[SMSOutbox, SMSOutboxResponseDTO]):
    def __init__(
        self, 
        uow: IUnitOfWork,
        kifiyaSmsProvider: KifiyaSMSProvider,
        jasminSmsProvider: JasminSMSProvider,
        afromessageSmsProvider: AfromessageSMSProvider
    ):
        super().__init__(uow, SMSOutbox, SMSOutboxResponseDTO)
        self.uow = uow
        # Build providers dictionary for immediate retry
        self.sms_providers = {
            "kifiya": kifiyaSmsProvider,
            "jasmin": jasminSmsProvider,
            "afromessage": afromessageSmsProvider
        }
    
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
        """Retry a failed SMS outbox message immediately (force processing).
        
        This method attempts to send the message immediately instead of just 
        marking it as pending for the background worker.
        
        Args:
            outbox_id: UUID of the outbox message to retry
            
        Returns:
            SMSOutboxResponseDTO with updated status and retry information
            
        Raises:
            EntityNotFoundError: If outbox message not found
            ValidationError: If template or configuration is invalid
        """
        async with self.uow:
            # Get the outbox entity
            outbox = await self.uow.smsOutboxes.getById(outbox_id)
            if not outbox:
                raise EntityNotFoundError(f"SMS outbox with id {outbox_id} not found")
            
            # Load template to get tenant info
            template = await self.uow.smsTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for SMS outbox {outbox_id}")
                raise ValidationError(f"Template {outbox.templateId} not found for outbox message")
            
            tenant_id = template.tenantId
            
            # Load tenant SMS configurations
            configs = await self.uow.tenantSmsConfigurations.find(
                lambda c: c.tenantId == tenant_id and c.isActive
            )
            if not configs:
                logger.error(f"No active SMS config found for tenant {tenant_id}")
                raise ValidationError(f"No active SMS configuration found for tenant {tenant_id}")
            
            # Select provider (priority 1 or lowest priority)
            config = min(configs, key=lambda c: c.priority)
            provider_name = (config.providerName or "").lower()
            
            # Get provider instance
            provider = self.sms_providers.get(provider_name)
            if not provider:
                logger.error(f"SMS provider '{provider_name}' not found")
                raise ValidationError(f"SMS provider '{provider_name}' not found")
            
            # Update retry attempt info
            outbox.retryCount += 1
            outbox.lastRetryAt = datetime.utcnow()
            outbox.updatedAt = datetime.utcnow()
            
            try:
                # Attempt to send via provider
                logger.info(f"Manual retry: sending SMS outbox {outbox_id} to {outbox.recipientNumber} via {provider_name}")
                success, error_msg = await provider.send_raw(
                    recipient=outbox.recipientNumber,
                    message=outbox.messageContent,
                    tenantConfig=config
                )
                
                if success:
                    # Success - move to notifications table
                    logger.info(f"SMS outbox {outbox_id} sent successfully, moving to notifications")
                    notification = SMSNotification(
                        id=uuid4(),
                        recipientNumber=outbox.recipientNumber,
                        messageContent=outbox.messageContent,
                        templateId=outbox.templateId,
                        status=NotificationStatus.SENT,
                        idempotencyKey=outbox.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.uow.smsNotifications.add(notification)
                    
                    # Delete from outbox
                    await self.uow.smsOutboxes.delete(outbox.id)
                    await self.uow.commit()
                    
                    # Return success response (outbox is deleted, return notification as outbox format)
                    outbox.status = NotificationStatus.SENT
                    outbox.isSent = True
                    outbox.sentAt = datetime.utcnow()
                    loader_options = [
                        selectinload(SmsOutboxModel.template).selectinload(SmsTemplateModel.tenant)
                    ]
                    # Note: outbox is deleted, so we return the last state before deletion
                    return SMSOutboxResponseDTO.fromEntityWithRelations(outbox)
                else:
                    # Failure - update retry info
                    logger.warning(f"SMS outbox {outbox_id} retry failed: {error_msg}")
                    outbox.lastErrorMessage = error_msg
                    outbox.status = NotificationStatus.FAILED
                    
                    # Update outbox
                    await self.uow.smsOutboxes.update(outbox)
                    await self.uow.commit()
                    
                    # Reload with relationships for response
                    loader_options = [
                        selectinload(SmsOutboxModel.template).selectinload(SmsTemplateModel.tenant)
                    ]
                    updated_outbox = await self.uow.smsOutboxes.getById(outbox_id, loader_options=loader_options)
                    return SMSOutboxResponseDTO.fromEntityWithRelations(updated_outbox)
                    
            except Exception as e:
                # Handle unexpected errors during send attempt
                logger.error(f"Error during manual retry of SMS outbox {outbox_id}: {e}", exc_info=True)
                error_message = f"{type(e).__name__}: {str(e) or 'Unknown error during send attempt'}"
                outbox.lastErrorMessage = error_message
                outbox.status = NotificationStatus.FAILED
                
                # Update outbox
                await self.uow.smsOutboxes.update(outbox)
                await self.uow.commit()
                
                # Reload with relationships for response
                loader_options = [
                    selectinload(SmsOutboxModel.template).selectinload(SmsTemplateModel.tenant)
                ]
                updated_outbox = await self.uow.smsOutboxes.getById(outbox_id, loader_options=loader_options)
                return SMSOutboxResponseDTO.fromEntityWithRelations(updated_outbox)
