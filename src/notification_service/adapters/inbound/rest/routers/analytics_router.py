from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends, Query
from qena_shared_lib.http import ControllerBase, api_controller, get

from notification_service.adapters.inbound.dto.analytics_dto import (
    AnalyticsOverviewResponseDTO,
    AnalyticsVolumeResponseDTO,
    AnalyticsFunnelResponseDTO,
    AnalyticsTenantsResponseDTO,
    AnalyticsChannelsResponseDTO,
    AnalyticsProvidersResponseDTO,
    AnalyticsErrorsResponseDTO,
    AnalyticsTemplatesResponseDTO,
)
from notification_service.application.services.dashboard_service import DashboardService
from notification_service.adapters.inbound.dependencies import require_role


@api_controller(prefix="/admin/analytics", tags=["Admin Analytics"])
class AnalyticsController(ControllerBase):
    def __init__(self, dashboardService: DashboardService = Depends()):
        self.dashboardService = dashboardService

    @get("/overview", response_model=AnalyticsOverviewResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_overview(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        tenantId: Optional[UUID] = Query(None, description="Optional tenant filter"),
    ):
        return await self.dashboardService.getAnalyticsOverview(startDate, endDate, channel=channel, tenant_id=tenantId)

    @get("/volume", response_model=AnalyticsVolumeResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_volume(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        granularity: str = Query("day", description="Aggregation granularity (hour, day, week)"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        tenantId: Optional[UUID] = Query(None, description="Optional tenant filter"),
    ):
        return await self.dashboardService.getAnalyticsVolume(startDate, endDate, granularity, channel=channel, tenant_id=tenantId)

    @get("/funnel", response_model=AnalyticsFunnelResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_funnel(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        tenantId: Optional[UUID] = Query(None, description="Optional tenant filter"),
    ):
        return await self.dashboardService.getAnalyticsFunnel(startDate, endDate, channel=channel, tenant_id=tenantId)

    @get("/tenants", response_model=AnalyticsTenantsResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_tenants(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        sortBy: str = Query("volume", description="Sort by (volume, deliveryRate, failedCount)"),
        limit: int = Query(50, description="Max tenants to return", ge=1, le=100),
    ):
        return await self.dashboardService.getAnalyticsTenants(startDate, endDate, sortBy=sortBy, limit=limit)

    @get("/channels", response_model=AnalyticsChannelsResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_channels(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
    ):
        return await self.dashboardService.getAnalyticsChannels(startDate, endDate)

    @get("/providers", response_model=AnalyticsProvidersResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_providers(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
    ):
        return await self.dashboardService.getAnalyticsProviders(startDate, endDate)

    @get("/errors", response_model=AnalyticsErrorsResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_errors(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        tenantId: Optional[UUID] = Query(None, description="Optional tenant filter"),
        limit: int = Query(10, description="Max errors to return", ge=1, le=50),
    ):
        return await self.dashboardService.getAnalyticsErrors(startDate, endDate, channel=channel, limit=limit, tenant_id=tenantId)

    @get("/templates", response_model=AnalyticsTemplatesResponseDTO, dependencies=[Depends(require_role("super-admin"))])
    async def get_templates(
        self,
        startDate: datetime = Query(..., description="Start date for analytics period"),
        endDate: datetime = Query(..., description="End date for analytics period"),
        channel: Optional[str] = Query(None, description="Optional channel filter"),
        tenantId: Optional[UUID] = Query(None, description="Optional tenant filter"),
        limit: int = Query(50, description="Max templates to return", ge=1, le=100),
    ):
        return await self.dashboardService.getAnalyticsTemplates(startDate, endDate, channel=channel, limit=limit, tenant_id=tenantId)
