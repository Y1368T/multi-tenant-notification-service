from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.whatsapp.whatsapp_outbox import WhatsAppOutbox
from notification_service.adapters.inbound.dto.whatsapp_outbox_response_dto import WhatsAppOutboxResponseDTO
from notification_service.adapters.inbound.dto.whatsapp_outbox_filter_dto import WhatsAppOutboxFilterDTO
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
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.domain.entities.whatsapp.whatsapp_notification import WhatsAppNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.infrastructure.providers.whatsapp.meta_cloud_provider import WhatsAppMetaCloudProvider
import logging

logger = logging.getLogger(__name__)

class WhatsAppOutboxService(BaseService[WhatsAppOutbox, WhatsAppOutboxResponseDTO]):
    def __init__(
        self,
        uow: IUnitOfWork,
        metaCloudProvider: WhatsAppMetaCloudProvider
    ):
        super().__init__(uow, WhatsAppOutbox, WhatsAppOutboxResponseDTO)
        self.uow = uow
        # Build providers dictionary for immediate retry
        self.whatsapp_providers = {
            "meta_cloud": metaCloudProvider
        }

    def _get_repository(self):
        """Get WhatsApp outbox repository."""
        return self.uow.whatsAppOutboxes

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        if hasattr(params, 'recipientNumber') and params.recipientNumber:
            filters["recipientNumber"] = params.recipientNumber
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for WhatsApp outbox."""
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
        """Get relationship paths to eager load for WhatsApp outbox."""
        return ["template", "template.tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for WhatsApp outbox."""
        return ["recipientNumber", "template.templateName", "template.serviceName", "template.tenant.name"]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for WhatsApp outbox."""
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

    async def retry(self, outbox_id: UUID) -> WhatsAppOutboxResponseDTO:
        """Retry a failed WhatsApp outbox message immediately (force processing).

        This method attempts to send the message immediately instead of just
        marking it as pending for the background worker.

        Args:
            outbox_id: UUID of the outbox message to retry

        Returns:
            WhatsAppOutboxResponseDTO with updated status and retry information

        Raises:
            EntityNotFoundError: If outbox message not found
            ValidationError: If template or configuration is invalid
        """
        async with self.uow:
            # Get the outbox entity
            outbox = await self.uow.whatsAppOutboxes.getById(outbox_id)
            if not outbox:
                raise EntityNotFoundError(f"WhatsApp outbox with id {outbox_id} not found")

            # Load template to get tenant info
            template = await self.uow.whatsAppTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for WhatsApp outbox {outbox_id}")
                raise ValidationError(f"Template {outbox.templateId} not found for outbox message")

            tenant_id = template.tenantId

            # Load tenant WhatsApp configurations
            configs = await self.uow.tenantWhatsAppConfigurations.find(
                lambda c: c.tenantId == tenant_id and c.isActive
            )
            if not configs:
                logger.error(f"No active WhatsApp config found for tenant {tenant_id}")
                raise ValidationError(f"No active WhatsApp configuration found for tenant {tenant_id}")

            # Select provider (priority 1 or lowest priority)
            config = min(configs, key=lambda c: c.priority)
            provider_name = (config.providerName or "").lower()

            # Get provider instance
            provider = self.whatsapp_providers.get(provider_name)
            if not provider:
                logger.error(f"WhatsApp provider '{provider_name}' not found")
                raise ValidationError(f"WhatsApp provider '{provider_name}' not found")

            # Update retry attempt info
            outbox.retryCount += 1
            outbox.lastRetryAt = datetime.utcnow()
            outbox.updatedAt = datetime.utcnow()

            try:
                # Attempt to send via provider
                logger.info(f"Manual retry: sending WhatsApp outbox {outbox_id} to {outbox.recipientNumber} via {provider_name}")
                success, error_msg = await provider.send_raw(
                    recipient=outbox.recipientNumber,
                    message=outbox.messageContent,
                    tenantConfig=config
                )

                if success:
                    # Success - move to notifications table
                    logger.info(f"WhatsApp outbox {outbox_id} sent successfully, moving to notifications")
                    notification = WhatsAppNotification(
                        id=uuid4(),
                        recipientNumber=outbox.recipientNumber,
                        messageContent=outbox.messageContent,
                        templateId=outbox.templateId,
                        status=NotificationStatus.SENT,
                        idempotencyKey=outbox.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.uow.whatsAppNotifications.add(notification)

                    # Delete from outbox
                    await self.uow.whatsAppOutboxes.delete(outbox.id)
                    await self.uow.commit()

                    # Return success response (outbox is deleted, return notification as outbox format)
                    outbox.status = NotificationStatus.SENT
                    outbox.isSent = True
                    outbox.sentAt = datetime.utcnow()
                    loader_options = [
                        selectinload(WhatsAppOutboxModel.template).selectinload(WhatsAppTemplateModel.tenant)
                    ]
                    # Note: outbox is deleted, so we return the last state before deletion
                    return WhatsAppOutboxResponseDTO.fromEntityWithRelations(outbox)
                else:
                    # Failure - update retry info
                    logger.warning(f"WhatsApp outbox {outbox_id} retry failed: {error_msg}")
                    outbox.lastErrorMessage = error_msg
                    outbox.status = NotificationStatus.FAILED

                    # Update outbox
                    await self.uow.whatsAppOutboxes.update(outbox)
                    await self.uow.commit()

                    # Reload with relationships for response
                    loader_options = [
                        selectinload(WhatsAppOutboxModel.template).selectinload(WhatsAppTemplateModel.tenant)
                    ]
                    updated_outbox = await self.uow.whatsAppOutboxes.getById(outbox_id, loader_options=loader_options)
                    return WhatsAppOutboxResponseDTO.fromEntityWithRelations(updated_outbox)

            except Exception as e:
                # Handle unexpected errors during send attempt
                logger.error(f"Error during manual retry of WhatsApp outbox {outbox_id}: {e}", exc_info=True)
                error_message = f"{type(e).__name__}: {str(e) or 'Unknown error during send attempt'}"
                outbox.lastErrorMessage = error_message
                outbox.status = NotificationStatus.FAILED

                # Update outbox
                await self.uow.whatsAppOutboxes.update(outbox)
                await self.uow.commit()

                # Reload with relationships for response
                loader_options = [
                    selectinload(WhatsAppOutboxModel.template).selectinload(WhatsAppTemplateModel.tenant)
                ]
                updated_outbox = await self.uow.whatsAppOutboxes.getById(outbox_id, loader_options=loader_options)
                return WhatsAppOutboxResponseDTO.fromEntityWithRelations(updated_outbox)
