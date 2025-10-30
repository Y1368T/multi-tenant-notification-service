from enum import Enum


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"
