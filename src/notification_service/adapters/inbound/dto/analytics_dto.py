from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AnalyticsOverviewResponseDTO(BaseModel):
    totalSent: int
    totalDelivered: int
    totalFailed: int
    deliveryRate: float
    model_config = ConfigDict(extra="forbid")


class AnalyticsVolumeSeriesItemDTO(BaseModel):
    date: str
    sent: int
    delivered: int
    failed: int


class AnalyticsVolumeResponseDTO(BaseModel):
    data: List[AnalyticsVolumeSeriesItemDTO]
    model_config = ConfigDict(extra="forbid")


class AnalyticsFunnelResponseDTO(BaseModel):
    sent: int
    delivered: int
    failed: int
    model_config = ConfigDict(extra="forbid")


class AnalyticsTenantItemDTO(BaseModel):
    tenantId: str
    tenantName: str
    totalMessages: int
    delivered: int
    deliveryRate: float
    channels: List[str]


class AnalyticsTenantsResponseDTO(BaseModel):
    items: List[AnalyticsTenantItemDTO]
    model_config = ConfigDict(extra="forbid")


class AnalyticsChannelItemDTO(BaseModel):
    channel: str
    sent: int
    delivered: int
    failed: int
    deliveryRate: float


class AnalyticsChannelsResponseDTO(BaseModel):
    channels: List[AnalyticsChannelItemDTO]
    model_config = ConfigDict(extra="forbid")


class AnalyticsProviderItemDTO(BaseModel):
    providerName: str
    sent: int
    delivered: int
    failed: int
    deliveryRate: float


class AnalyticsProvidersResponseDTO(BaseModel):
    providers: List[AnalyticsProviderItemDTO]
    model_config = ConfigDict(extra="forbid")


class AnalyticsErrorItemDTO(BaseModel):
    message: str
    count: int


class AnalyticsErrorsResponseDTO(BaseModel):
    errors: List[AnalyticsErrorItemDTO]
    model_config = ConfigDict(extra="forbid")


class AnalyticsTemplateItemDTO(BaseModel):
    templateId: Optional[str]
    templateName: Optional[str]
    sent: int
    delivered: int
    failed: int
    deliveryRate: float


class AnalyticsTemplatesResponseDTO(BaseModel):
    templates: List[AnalyticsTemplateItemDTO]
    model_config = ConfigDict(extra="forbid")
