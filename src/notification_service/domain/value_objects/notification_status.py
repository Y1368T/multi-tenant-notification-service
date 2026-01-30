class NotificationStatus:
    """Enumeration of possible notification statuses."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"
    PERMANENTLY_FAILED = "permanently_failed"  # After max retries exceeded