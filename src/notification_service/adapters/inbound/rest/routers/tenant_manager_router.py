from fastapi import Depends, Request, Query
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, delete
from uuid import UUID
from typing import List, Optional, Any
from datetime import datetime

from notification_service.adapters.inbound.dependencies import require_role
from notification_service.application.services.dashboard_service import DashboardService
from notification_service.adapters.inbound.dto.dashboard_dto import DashboardStatsResponseDTO
from notification_service.adapters.inbound.dto.analytics_dto import (
    AnalyticsOverviewResponseDTO,
    AnalyticsVolumeResponseDTO,
    AnalyticsTemplatesResponseDTO,
)

@api_controller(prefix="/tenant", tags=["Tenant Manager API"])
class TenantManagerAPIController(ControllerBase):
    def __init__(self, dashboardService: DashboardService = Depends()):
        self.dashboardService = dashboardService

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
    @get("/dashboard/stats", response_model=DashboardStatsResponseDTO, dependencies=[Depends(require_role("tenant-manager"))])
    async def get_dashboard_stats(self, request: Request, period: str = Query("24h", description="24h|7d|30d")):
        tenant_id = request.state.user.get("tenant_id")
        result = await self.dashboardService.getStats(period, tenant_id=tenant_id)
        return DashboardStatsResponseDTO(**result)

    @get("/analytics/overview", response_model=AnalyticsOverviewResponseDTO, dependencies=[Depends(require_role("tenant-manager"))])
    async def get_analytics_overview(
        self,
        request: Request,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
    ):
        tenant_id = request.state.user.get("tenant_id")
        return await self.dashboardService.getAnalyticsOverview(startDate, endDate, channel=channel, tenant_id=tenant_id)

    @get("/analytics/volume", response_model=AnalyticsVolumeResponseDTO, dependencies=[Depends(require_role("tenant-manager"))])
    async def get_analytics_volume(
        self,
        request: Request,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        granularity: str = Query("day", description="Aggregation granularity (hour, day, week)"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
    ):
        tenant_id = request.state.user.get("tenant_id")
        return await self.dashboardService.getAnalyticsVolume(startDate, endDate, granularity, channel=channel, tenant_id=tenant_id)

    @get("/analytics/templates", response_model=AnalyticsTemplatesResponseDTO, dependencies=[Depends(require_role("tenant-manager"))])
    async def get_analytics_templates(
        self,
        request: Request,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        limit: int = Query(50, description="Max templates to return", ge=1, le=100),
    ):
        tenant_id = request.state.user.get("tenant_id")
        return await self.dashboardService.getAnalyticsTemplates(startDate, endDate, channel=channel, tenant_id=tenant_id, limit=limit)
