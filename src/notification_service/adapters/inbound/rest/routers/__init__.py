from qena_shared_lib.application import Builder
from notification_service.adapters.inbound.rest.routers.tenant_routers import TenantController
from notification_service.adapters.inbound.rest.routers.sms_notification_router import SMSNotificationController
from notification_service.adapters.inbound.rest.routers.tenant_sms_configuration import TenantSMSConfigurationController
from notification_service.adapters.inbound.rest.routers.sms_template_router import SMSTemplateController
from notification_service.adapters.inbound.rest.routers.provider_supported_router import ProviderSupportedController
def register_controllers(builder: Builder) -> None:
    builder.with_controllers(
        TenantController,
        SMSNotificationController,
        TenantSMSConfigurationController,
        SMSTemplateController,
        ProviderSupportedController
    )