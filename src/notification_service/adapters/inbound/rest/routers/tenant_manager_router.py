from fastapi import Depends, Request, Query
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, delete
from uuid import UUID
from typing import List, Optional, Any

@api_controller(prefix="/api/tenant", tags=["Tenant Manager API"])
class TenantManagerAPIController(ControllerBase):
    def __init__(self):
        pass

    # --- Channels (Read Only) ---
    @get("/channels")
    async def get_channels(self, request: Request) -> Any:
        """Read-only view of channels assigned to the tenant."""
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"List of channels for tenant {tenant_id}", "tenant_id": tenant_id}

    # --- Templates ---
    @get("/templates")
    async def get_templates(self, request: Request) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"List of templates for tenant {tenant_id}", "tenant_id": tenant_id}

    @post("/templates")
    async def create_template(self, request: Request, payload: dict) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Template created for tenant {tenant_id}", "data": payload}
        
    @put("/templates/{template_id}")
    async def update_template(self, template_id: UUID, request: Request, payload: dict) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Template {template_id} updated for tenant {tenant_id}", "data": payload}

    @delete("/templates/{template_id}")
    async def delete_template(self, template_id: UUID, request: Request) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Template {template_id} deleted for tenant {tenant_id}"}

    # --- Messages ---
    @post("/messages/send")
    async def send_message(self, request: Request, payload: dict) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Message queued for tenant {tenant_id}", "message_id": "stubbed-msg-id", "data": payload}

    # --- Outbox ---
    @get("/outbox")
    async def get_outbox(self, request: Request, page: int = 1, limit: int = 20) -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Outbox for tenant {tenant_id}", "tenant_id": tenant_id, "page": page, "limit": limit}

    # --- Analytics (Tenant-scoped) ---
    @get("/analytics")
    async def get_analytics(self, request: Request, period: str = "7d") -> Any:
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"message": f"Analytics for tenant {tenant_id} (Stubbed)", "tenant_id": tenant_id}
