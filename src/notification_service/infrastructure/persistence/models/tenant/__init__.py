from .tenant_email_configuration import TenantEmailConfigurationModel
from .tenant_sms_configuration import TenantSMSConfigurationModel
#new
from .tenant_whatsapp_configuration import TenantWhatsAppConfigurationModel
#new
from .tenant import TenantModel
__all__ = [
    "TenantModel",
    "TenantEmailConfigurationModel",
    "TenantSMSConfigurationModel",
    #new
    "TenantWhatsAppConfigurationModel"
    #new
]