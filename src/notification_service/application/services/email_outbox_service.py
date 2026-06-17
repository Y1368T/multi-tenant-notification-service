"""Email outbox service following the same pattern as SMSOutboxService."""
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.orm import selectinload

from notification_service.application.services.base_service import BaseService
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.email_outbox_dto import EmailOutboxResponseDTO
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp,
)
from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError, ValidationError
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel
from notification_service.infrastructure.providers.email.smtp_provider import SMTPProvider

logger = logging.getLogger(__name__)


class EmailOutboxService(BaseService[EmailOutbox, EmailOutboxResponseDTO]):
    """Service for managing email outbox entries."""

    def __init__(self, uow: IUnitOfWork, smtpProvider: SMTPProvider):
        super().__init__(uow, EmailOutbox, EmailOutboxResponseDTO)
        self.uow = uow
        self.email_provider = smtpProvider

    def _get_repository(self):
        """Get Email outbox repository."""
        return self.uow.emailOutbox

    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, "status") and params.status:
            filters["status"] = params.status
        if hasattr(params, "recipientEmail") and params.recipientEmail:
            filters["recipientEmail"] = params.recipientEmail
        return filters

    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for Email outbox."""
        related_filters: List[RelatedFilter] = []

        # Filter by tenantId through template
        if hasattr(params, "tenantId") and params.tenantId:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="tenantId",
                    op=FilterOp.EQ,
                    value=UUID(params.tenantId)
                    if isinstance(params.tenantId, str)
                    else params.tenantId,
                )
            )

        # Filter by templateName
        if hasattr(params, "templateName") and params.templateName:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="templateName",
                    op=FilterOp.EQ,
                    value=params.templateName,
                )
            )

        # Filter by serviceName
        if hasattr(params, "serviceName") and params.serviceName:
            related_filters.append(
                RelatedFilter(
                    relationshipPath="template",
                    field="serviceName",
                    op=FilterOp.EQ,
                    value=params.serviceName,
                )
            )

        return related_filters

    def _get_includes(self) -> List[str]:
        """Get relationship paths to eager load for Email outbox."""
        return ["template", "template.tenant"]

    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for Email outbox."""
        return [
            "recipientEmail",
            "template.templateName",
            "template.serviceName",
            "template.tenant.name",
        ]

    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for Email outbox."""
        # Build root filters
        root_filters = {}
        if hasattr(params, "id") and params.id:
            try:
                root_filters["id"] = (
                    UUID(params.id) if isinstance(params.id, str) else params.id
                )
            except (ValueError, AttributeError):
                root_filters["id"] = params.id

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
            includes=includes,
        )

    async def retry(self, outbox_id: UUID) -> EmailOutboxResponseDTO:
        """Retry a failed Email outbox message immediately (force processing).

        This method attempts to send the email immediately instead of just 
        marking it as pending for the background worker.

        Args:
            outbox_id: UUID of the outbox message to retry

        Returns:
            EmailOutboxResponseDTO with updated status and retry information

        Raises:
            EntityNotFoundError: If outbox message not found
            ValidationError: If template or configuration is invalid
        """
        async with self.uow:
            # Get the outbox entity
            outbox = await self.uow.emailOutbox.getById(outbox_id)
            if not outbox:
                raise EntityNotFoundError(f"Email outbox with id {outbox_id} not found")

            # Load template to get tenant info
            template = await self.uow.emailTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for Email outbox {outbox_id}")
                raise ValidationError(f"Template {outbox.templateId} not found for outbox message")

            tenant_id = template.tenantId

            # Load tenant email configurations
            configs = await self.uow.tenantEmailConfigurations.find(
                lambda c: c.tenantId == tenant_id and c.isActive
            )
            if not configs:
                logger.error(f"No active Email config found for tenant {tenant_id}")
                raise ValidationError(f"No active Email configuration found for tenant {tenant_id}")

            config = configs[0]  # Use first active config

            # Update retry attempt info
            outbox.retryCount += 1
            outbox.lastRetryAt = datetime.utcnow()
            outbox.updatedAt = datetime.utcnow()

            try:
                # Attempt to send via provider
                logger.info(f"Manual retry: sending Email outbox {outbox_id} to {outbox.recipientEmail}")
                success, error_msg = await self.email_provider.send_raw(
                    recipient=outbox.recipientEmail,
                    messageContent=outbox.messageContent,
                    tenantConfig=config
                )

                if success:
                    # Success - move to notifications table
                    logger.info(f"Email outbox {outbox_id} sent successfully, moving to notifications")
                    notification = EmailNotification(
                        id=uuid4(),
                        recipientEmail=outbox.recipientEmail,
                        messageContent=outbox.messageContent,
                        templateId=outbox.templateId,
                        status=NotificationStatus.SENT,
                        idempotencyKey=outbox.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.uow.emailNotifications.add(notification)

                    # Delete from outbox
                    await self.uow.emailOutbox.delete(outbox.id)
                    await self.uow.commit()

                    # Return success response
                    outbox.status = NotificationStatus.SENT
                    outbox.isSent = True
                    outbox.sentAt = datetime.utcnow()
                    return EmailOutboxResponseDTO.fromEntityWithRelations(outbox)
                else:
                    # Failure - update retry info
                    logger.warning(f"Email outbox {outbox_id} retry failed: {error_msg}")
                    outbox.lastErrorMessage = error_msg
                    outbox.status = NotificationStatus.FAILED

                    # Update outbox
                    await self.uow.emailOutbox.update(outbox)
                    await self.uow.commit()

                    # Reload with relationships for response
                    loader_options = [
                        selectinload(EmailOutboxModel.template).selectinload(
                            EmailTemplateModel.tenant
                        )
                    ]
                    updated_outbox = await self.uow.emailOutbox.getById(
                        outbox_id, loader_options=loader_options
                    )
                    return EmailOutboxResponseDTO.fromEntityWithRelations(updated_outbox)

            except Exception as e:
                # Handle unexpected errors during send attempt
                logger.error(f"Error during manual retry of Email outbox {outbox_id}: {e}", exc_info=True)
                error_message = f"{type(e).__name__}: {str(e) or 'Unknown error during send attempt'}"
                outbox.lastErrorMessage = error_message
                outbox.status = NotificationStatus.FAILED

                # Update outbox
                await self.uow.emailOutbox.update(outbox)
                await self.uow.commit()

                # Reload with relationships for response
                loader_options = [
                    selectinload(EmailOutboxModel.template).selectinload(
                        EmailTemplateModel.tenant
                    )
                ]
                updated_outbox = await self.uow.emailOutbox.getById(
                    outbox_id, loader_options=loader_options
                )
                return EmailOutboxResponseDTO.fromEntityWithRelations(updated_outbox)
