from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, Query
from qena_shared_lib.http import ControllerBase, api_controller, get

from notification_service.adapters.inbound.dto.dashboard_dto import (
    DashboardActivityResponseDTO,
    DashboardProviderHealthResponseDTO,
    DashboardStatsResponseDTO,
    DashboardVolumeResponseDTO,
)
from notification_service.adapters.inbound.dependencies import require_role
from notification_service.application.services.dashboard_service import DashboardService


@api_controller(prefix="/admin/dashboard", tags=["Admin Dashboard"])
class DashboardController(ControllerBase):
    def __init__(self, dashboardService: DashboardService = Depends()):
        self.dashboardService = dashboardService

    @get("/stats", response_model=DashboardStatsResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def stats(
        self,
        period: str = Query("24h", description="24h|7d|30d"),
    ) -> DashboardStatsResponseDTO:
        """KPI stat cards: tenant/message counts, delivery rate, period-over-period deltas."""
        result = await self.dashboardService.getStats(period)
        return DashboardStatsResponseDTO(**result)

    @get("/volume", response_model=DashboardVolumeResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def volume(
        self,
        period: str = Query("7d", description="7d|30d|90d"),
        granularity: str = Query("day", description="hour|day|week"),
        channel: Optional[str] = Query(None, description="sms|email|inapp|whatsapp (omit for all channels)"),
    ) -> DashboardVolumeResponseDTO:
        """Delivery volume over time, for the line chart."""
        result = await self.dashboardService.getVolume(period, granularity, channel)
        return DashboardVolumeResponseDTO(**result)

    @get("/provider-health", response_model=DashboardProviderHealthResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def providerHealth(self) -> DashboardProviderHealthResponseDTO:
        """Live provider status + all-time success rate."""
        result = await self.dashboardService.getProviderHealth()
        return DashboardProviderHealthResponseDTO(**result)

    @get("/activity", response_model=DashboardActivityResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def activityFeed(
        self,
        limit: int = Query(20, description="Max items to return", ge=1, le=100),
    ) -> DashboardActivityResponseDTO:
        """Recent activity feed."""
        result = await self.dashboardService.getActivityFeed(limit)
        return DashboardActivityResponseDTO(**result)

    # End of DashboardController
