from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, Query
from qena_shared_lib.http import ControllerBase, api_controller, get

from notification_service.adapters.inbound.dto.dashboard_dto import (
    DashboardActivityResponseDTO,
    DashboardChannelsResponseDTO,
    DashboardProviderHealthResponseDTO,
    DashboardStatsResponseDTO,
    DashboardTopTenantsResponseDTO,
    DashboardVolumeResponseDTO,
    FailuresResponseDTO,
    SentMessagesResponseDTO,
)
from notification_service.application.services.dashboard_service import DashboardService


@api_controller(prefix="/admin/dashboard", tags=["Admin Dashboard"])
class DashboardController(ControllerBase):
    def __init__(self, dashboardService: DashboardService = Depends()):
        self.dashboardService = dashboardService

    @get("/stats", response_model=DashboardStatsResponseDTO)
    async def stats(
        self,
        period: str = Query("24h", description="24h|7d|30d"),
    ) -> DashboardStatsResponseDTO:
        """KPI stat cards: tenant/message counts, delivery rate, period-over-period deltas."""
        result = await self.dashboardService.getStats(period)
        return DashboardStatsResponseDTO(**result)

    @get("/volume", response_model=DashboardVolumeResponseDTO)
    async def volume(
        self,
        period: str = Query("7d", description="7d|30d|90d"),
        granularity: str = Query("day", description="hour|day|week"),
        channel: Optional[str] = Query(None, description="sms|email|inapp|whatsapp (omit for all channels)"),
    ) -> DashboardVolumeResponseDTO:
        """Delivery volume over time, for the line chart."""
        result = await self.dashboardService.getVolume(period, granularity, channel)
        return DashboardVolumeResponseDTO(**result)

    @get("/channels", response_model=DashboardChannelsResponseDTO)
    async def channels(
        self,
        period: str = Query("24h", description="24h|7d|30d"),
    ) -> DashboardChannelsResponseDTO:
        """Per-channel sent/delivered/failed breakdown."""
        result = await self.dashboardService.getChannelBreakdown(period)
        return DashboardChannelsResponseDTO(**result)

    @get("/activity", response_model=DashboardActivityResponseDTO)
    async def activity(
        self,
        limit: int = Query(20, ge=1, le=100),
    ) -> DashboardActivityResponseDTO:
        """Recent activity feed (delivered / failed / retry / tenant_created)."""
        result = await self.dashboardService.getActivity(limit)
        return DashboardActivityResponseDTO(**result)

    @get("/top-tenants", response_model=DashboardTopTenantsResponseDTO)
    async def topTenants(
        self,
        limit: int = Query(5, ge=1, le=50),
        period: str = Query("7d", description="7d|30d"),
    ) -> DashboardTopTenantsResponseDTO:
        """Top tenants ranked by message volume."""
        result = await self.dashboardService.getTopTenants(limit, period)
        return DashboardTopTenantsResponseDTO(**result)

    @get("/provider-health", response_model=DashboardProviderHealthResponseDTO)
    async def providerHealth(self) -> DashboardProviderHealthResponseDTO:
        """Live provider status + all-time success rate."""
        result = await self.dashboardService.getProviderHealth()
        return DashboardProviderHealthResponseDTO(**result)

    @get("/failures", response_model=FailuresResponseDTO)
    async def failures(
        self,
        period: str = Query("24h", description="24h|7d|30d"),
    ) -> FailuresResponseDTO:
        """Failed-message summary: totals, by channel, by provider, top error reasons."""
        result = await self.dashboardService.getFailures(period)
        return FailuresResponseDTO(**result)


@api_controller(prefix="/admin/analytics", tags=["Admin Analytics"])
class AnalyticsController(ControllerBase):
    def __init__(self, dashboardService: DashboardService = Depends()):
        self.dashboardService = dashboardService

    @get("/sent-messages", response_model=SentMessagesResponseDTO)
    async def sentMessages(
        self,
        tenantId: Optional[List[UUID]] = Query(None, description="Repeat to filter multiple tenants; omit for all"),
        channel: Optional[List[str]] = Query(None, description="Repeat to filter multiple channels; omit for all"),
        startDate: Optional[datetime] = Query(None, description="Inclusive range start; omit for no lower bound"),
        endDate: Optional[datetime] = Query(None, description="Exclusive range end; omit for no upper bound"),
        granularity: str = Query("day", description="day|week|month|none"),
    ) -> SentMessagesResponseDTO:
        """Message count aggregated by tenant x channel x time, with every
        dimension independently optional - see GUIDE.md for the full
        filtering design."""
        result = await self.dashboardService.getSentMessages(tenantId, channel, startDate, endDate, granularity)
        return SentMessagesResponseDTO(**result)
