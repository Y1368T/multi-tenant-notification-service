"""Background job processors for the notification service."""
from notification_service.infrastructure.jobs.outbox_processor import OutboxProcessor

__all__ = ["OutboxProcessor"]

