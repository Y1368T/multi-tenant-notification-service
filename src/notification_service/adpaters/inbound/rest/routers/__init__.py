from qena_shared_lib.application import Builder
from notification_service.adpaters.inbound.rest.routers.tenant_routers import TenantController
def register_controllers(builder: Builder) -> None:
    builder.with_controllers(
        TenantController,
    )