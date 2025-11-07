
from enum import Enum

class SMSProvider(Enum):
    ETHIOTELECOM = "ethiotelecom"
    AFROMESSAGE = "afromessage"
    KIFIYA = "kifiya"

class EmailProvider(Enum):
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    AMAZON_SES = "amazon_ses"
    SMTP = "smtp"

class PushProvider(Enum):
    FIREBASE = "firebase"
    ONESIGNAL = "onesignal"

