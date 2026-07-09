from .tenant import Tenant
from .tenant_email_configuration import TenantEmailConfiguration
from .tenant_sms_configuration import TenantSMSConfiguration
#new
from .tenant_whatsapp_configuration import TenantWhatsAppConfiguration
#new
__all__ = [
    "Tenant",
    "TenantEmailConfiguration",
    "TenantSMSConfiguration",
    #new(whatsapp)
    "TenantWhatsAppConfiguration"
]