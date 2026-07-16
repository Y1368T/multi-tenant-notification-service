from qena_shared_lib.application import Builder
from notification_service.adapters.inbound.rest.routers.tenant_routers import TenantController
from notification_service.adapters.inbound.rest.routers.sms_notification_router import SMSNotificationController
from notification_service.adapters.inbound.rest.routers.tenant_sms_configuration import TenantSMSConfigurationController
from notification_service.adapters.inbound.rest.routers.sms_template_router import SMSTemplateController
#Whatsapp
from notification_service.adapters.inbound.rest.routers.whatsapp_notification_router import WhatsAppNotificationController
from notification_service.adapters.inbound.rest.routers.tenant_whatsapp_configuration import TenantWhatsAppConfigurationController
from notification_service.adapters.inbound.rest.routers.whatsapp_template_router import WhatsAppTemplateController
from notification_service.adapters.inbound.rest.routers.whatsapp_outbox_router import WhatsAppOutboxController

from notification_service.adapters.inbound.rest.routers.provider_supported_router import ProviderSupportedController
from notification_service.adapters.inbound.rest.routers.in_app_notification_router import InAppNotificationController
from notification_service.adapters.inbound.rest.routers.in_app_template_router import InAppTemplateController
from notification_service.adapters.inbound.rest.routers.tenant_inapp_configuration_router import TenantInAppConfigurationController
from notification_service.adapters.inbound.rest.routers.sms_outbox_router import SMSOutboxController
from notification_service.adapters.inbound.rest.routers.in_app_outbox_router import InAppOutboxController
# Email controllers
from notification_service.adapters.inbound.rest.routers.email_notification_router import EmailNotificationController
from notification_service.adapters.inbound.rest.routers.email_template_router import EmailTemplateController
from notification_service.adapters.inbound.rest.routers.email_outbox_router import EmailOutboxController
from notification_service.adapters.inbound.rest.routers.tenant_email_configuration_router import TenantEmailConfigurationController

from notification_service.adapters.inbound.rest.routers.dashboard_router import (
        DashboardController,
        AnalyticsController,
    )

def register_controllers(builder: Builder) -> None:
    builder.with_controllers(
        TenantController,
        # SMS controllers
        SMSNotificationController,
        TenantSMSConfigurationController,
        SMSTemplateController,
        SMSOutboxController,
        # WhatsApp controllers
        WhatsAppNotificationController,
        TenantWhatsAppConfigurationController,
        WhatsAppTemplateController,
        WhatsAppOutboxController,
        # Admin Dashboard controllers
        DashboardController,
        AnalyticsController,
        # In-App controllers
        InAppNotificationController,
        InAppTemplateController,
        TenantInAppConfigurationController,
        InAppOutboxController,
        # Email controllers
        EmailNotificationController,
        EmailTemplateController,
        EmailOutboxController,
        TenantEmailConfigurationController,
        # Provider controller
        ProviderSupportedController,
    )