
from enum import Enum


class SMSProvider(Enum):
    AFROMESSAGE = "afromessage"
    KIFIYA = "kifiya"
    JASMIN = "jasmin"

class EmailProvider(Enum):
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    AMAZON_SES = "amazon_ses"
    SMTP = "smtp"

class PushProvider(Enum):
    FIREBASE = "fcm"
    ONESIGNAL = "onesignal"

class TelegramProvider(Enum):
    TELEGRAM = "telegram"
    