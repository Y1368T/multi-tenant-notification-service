from fastapi import Depends, Request, Query
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, delete
from uuid import UUID
from typing import List, Optional, Any

from notification_service.application.services.tenant_service import TenantService
from notification_service.application.services.provider_service import ProviderService

# Use a generic controller for the new Admin API
@api_controller(prefix="/api/admin", tags=["Admin API"])
class AdminAPIController(ControllerBase):
    def __init__(self, tenantService: TenantService = Depends(), providerService: ProviderService = Depends()):
        self.tenantService = tenantService
        self.providerService = providerService

    # --- Tenants ---
    @get("/tenants")
    async def get_tenants(self, request: Request) -> Any:
        """Get all tenants (Super Admin)"""
        # In real implementation: build PaginatedRequest and return self.tenantService.get()
        return {"message": "List of all tenants (stubbed)"}

    @post("/tenants")
    async def create_tenant(self, request: Request, payload: dict) -> Any:
        return {"message": "Tenant created", "data": payload}

    @put("/tenants/{tenant_id}")
    async def update_tenant(self, tenant_id: UUID, request: Request, payload: dict) -> Any:
        return {"message": f"Tenant {tenant_id} updated", "data": payload}

    @delete("/tenants/{tenant_id}")
    async def delete_tenant(self, tenant_id: UUID, request: Request) -> Any:
        return {"message": f"Tenant {tenant_id} deleted"}

    # --- Users ---
    @get("/users")
    async def get_users(self, request: Request) -> Any:
        return {"message": "List of users (stubbed)"}

    @post("/users")
    async def create_user(self, request: Request, payload: dict) -> Any:
        return {"message": "User created", "data": payload}

    @put("/users/{user_id}")
    async def update_user(self, user_id: UUID, request: Request, payload: dict) -> Any:
        return {"message": f"User {user_id} updated", "data": payload}

    @delete("/users/{user_id}")
    async def delete_user(self, user_id: UUID, request: Request) -> Any:
        return {"message": f"User {user_id} deactivated"}

    # --- Providers ---
    @get("/providers")
    async def get_providers(self, request: Request) -> Any:
        return {"message": "List of providers (stubbed)"}

    @post("/providers")
    async def create_provider(self, request: Request, payload: dict) -> Any:
        return {"message": "Provider registered", "data": payload}
        
    @put("/providers/{provider_id}")
    async def update_provider(self, provider_id: UUID, request: Request, payload: dict) -> Any:
        return {"message": f"Provider {provider_id} updated", "data": payload}

    @delete("/providers/{provider_id}")
    async def delete_provider(self, provider_id: UUID, request: Request) -> Any:
        return {"message": f"Provider {provider_id} deleted"}

    # --- Analytics (Stubs as per plan) ---
    @get("/analytics/overview")
    async def get_analytics_overview(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics overview stub for DB team to implement"}
        
    @get("/analytics/tenants")
    async def get_analytics_tenants(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics tenants stub for DB team to implement"}
        
    @get("/analytics/channels")
    async def get_analytics_channels(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics channels stub for DB team to implement"}
        
    @get("/analytics/providers")
    async def get_analytics_providers(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics providers stub for DB team to implement"}
        
    @get("/analytics/errors")
    async def get_analytics_errors(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics errors stub for DB team to implement"}
