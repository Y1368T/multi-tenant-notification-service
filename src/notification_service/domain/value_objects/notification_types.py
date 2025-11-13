from enum import Enum


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    SMS = "sms"
    EMAIL = "email"
    INAPP = "inapp"
    WHATSAPP = "whatsapp"
