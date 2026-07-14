# Tenant DTOs
from .tenant_request_dto import (
    TenantRequestDTO,
    TenantFilterDTO,
    TenantResponseDTO
)

# SMS Notification DTOs
from .sms_notification_request_dto import SMSNotificationFilterDTO
from .sms_notification_response_dto import SMSNotificationResponseDTO

# SMS Template DTOs
from .sms_template_request_dto import (
    SMSTemplateRequestDTO,
    SMSTemplateResponseDTO,
    SMSTemplateFilterDTO
)

# SMS Outbox DTOs
from .sms_outbox_request_dto import (
    SMSOutboxRequestDTO,
    SMSOutbocFilterDTO  # Note: typo in original file name
)
from .sms_outbox_filter_dto import SMSOutboxFilterDTO
from .sms_outbox_response_dto import SMSOutboxResponseDTO

# Tenant SMS Configuration DTOs
from .tenant_sms_confuguration_request_dto import (
    TenantSMSConfigurationRequestDto,
    TenantSMSConfigurationResponseDTO,
    TenantSMSConfigurationFilterDTO
)

#new
# WhatsApp Notification DTOs
from .whatsapp_notification_request_dto import WhatsAppNotificationFilterDTO
from .whatsapp_notification_response_dto import WhatsAppNotificationResponseDTO

# WhatsApp Template DTOs
from .whatsapp_template_request_dto import (
    WhatsAppTemplateRequestDTO,
    WhatsAppTemplateResponseDTO,
    WhatsAppTemplateFilterDTO
)

# WhatsApp Outbox DTOs
from .whatsapp_outbox_request_dto import (
    WhatsAppOutboxRequestDTO,
    WhatsAppOutbocFilterDTO  # Note: typo in original file name
)
from .whatsapp_outbox_filter_dto import WhatsAppOutboxFilterDTO
from .whatsapp_outbox_response_dto import WhatsAppOutboxResponseDTO

# Tenant WhatsApp Configuration DTOs
from .tenant_whatsapp_confuguration_request_dto import (
    TenantWhatsAppConfigurationRequestDto,
    TenantWhatsAppConfigurationResponseDTO,
    TenantWhatsAppConfigurationFilterDTO
)
#new

# Tenant InApp Configuration DTOs
from .tenant_inapp_configuration_request_dto import (
    TenantInAppConfigurationRequestDto,
    TenantInAppConfigurationResponseDTO,
    TenantInAppConfigurationFilterDTO
)

# In-App Notification DTOs
from .in_app_notification_request_dto import InAppNotificationFilterDTO
from .in_app_notification_response_dto import InAppNotificationResponseDTO

# In-App Template DTOs
from .in_app_template_request_dto import (
    InAppTemplateRequestDTO,
    InAppTemplateResponseDTO,
    InAppTemplateFilterDTO
)

# In-App Outbox DTOs
from .in_app_outbox_filter_dto import InAppOutboxFilterDTO
from .in_app_outbox_response_dto import InAppOutboxResponseDTO

# Provider Supported DTOs
from .provider_supported_dto import (
    TestRequestDto,
    ProviderSupportedDTO,
    ProviderResponseDTO,
    ProviderFilterDTO
)

# Pagination DTOs
from .paginated_request_dto import (
    PaginatedRequestDTO,
    SortDirection,
    FilterOp,
    RelatedFilter,
    PaginatedRequest
)
from .paginated_response_dto import PaginatedResponseDTO

__all__ = [
    # Tenant DTOs
    "TenantRequestDTO",
    "TenantFilterDTO",
    "TenantResponseDTO",
    
    # SMS Notification DTOs
    "SMSNotificationFilterDTO",
    "SMSNotificationResponseDTO",
    
    # SMS Template DTOs
    "SMSTemplateRequestDTO",
    "SMSTemplateResponseDTO",
    "SMSTemplateFilterDTO",
    
    # SMS Outbox DTOs
    "SMSOutboxRequestDTO",
    "SMSOutboxResponseDTO",
    "SMSOutboxFilterDTO",
    "SMSOutbocFilterDTO",  # Note: typo in original file
    
    # Tenant SMS Configuration DTOs
    "TenantSMSConfigurationRequestDto",
    "TenantSMSConfigurationResponseDTO",
    "TenantSMSConfigurationFilterDTO",

    #new
    # WhatsApp Notification DTOs
    "WhatsAppNotificationFilterDTO",
    "WhatsAppNotificationResponseDTO",
    
    # WhatsApp Template DTOs
    "WhatsAppTemplateRequestDTO",
    "WhatsAppTemplateResponseDTO",
    "WhatsAppTemplateFilterDTO",
    
    # WhatsApp Outbox DTOs
    "WhatsAppOutboxRequestDTO",
    "WhatsAppOutboxResponseDTO",
    "WhatsAppOutboxFilterDTO",
    "WhatsAppOutbocFilterDTO",  # Note: typo in original file
    
    # Tenant WhatsApp Configuration DTOs
    "TenantWhatsAppConfigurationRequestDto",
    "TenantWhatsAppConfigurationResponseDTO",
    "TenantWhatsAppConfigurationFilterDTO",
    #new
    
    # Tenant InApp Configuration DTOs
    "TenantInAppConfigurationRequestDto",
    "TenantInAppConfigurationResponseDTO",
    "TenantInAppConfigurationFilterDTO",
    
    # In-App Notification DTOs
    "InAppNotificationFilterDTO",
    "InAppNotificationResponseDTO",
    
    # In-App Template DTOs
    "InAppTemplateRequestDTO",
    "InAppTemplateResponseDTO",
    "InAppTemplateFilterDTO",
    
    # In-App Outbox DTOs
    "InAppOutboxFilterDTO",
    "InAppOutboxResponseDTO",
    
    # Provider Supported DTOs
    "TestRequestDto",
    "ProviderSupportedDTO",
    "ProviderResponseDTO",
    "ProviderFilterDTO",
    
    # Pagination DTOs
    "PaginatedRequestDTO",
    "PaginatedResponseDTO",
    "SortDirection",
    "FilterOp",
    "RelatedFilter",
    "PaginatedRequest"
]
