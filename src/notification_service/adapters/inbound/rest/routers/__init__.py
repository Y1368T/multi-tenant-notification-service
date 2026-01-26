from qena_shared_lib.application import Builder
from notification_service.adapters.inbound.rest.routers.tenant_routers import TenantController
from notification_service.adapters.inbound.rest.routers.sms_notification_router import SMSNotificationController
from notification_service.adapters.inbound.rest.routers.tenant_sms_configuration import TenantSMSConfigurationController
from notification_service.adapters.inbound.rest.routers.sms_template_router import SMSTemplateController
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


def register_controllers(builder: Builder) -> None:
    builder.with_controllers(
        TenantController,
        # SMS controllers
        SMSNotificationController,
        TenantSMSConfigurationController,
        SMSTemplateController,
        SMSOutboxController,
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