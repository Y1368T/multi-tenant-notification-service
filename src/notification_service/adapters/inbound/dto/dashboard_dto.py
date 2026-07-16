from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# 1. GET /admin/dashboard/stats
# ---------------------------------------------------------------------------
class MessagesByChannelDTO(BaseModel):
    sms: int
    email: int
    inapp: int
    whatsapp: int


class ComparedToPreviousDTO(BaseModel):
    
    totalMessages: str
    deliveryRate: str
    failedMessages: str


class DashboardStatsResponseDTO(BaseModel):
    totalTenants: int
    activeTenants: int
    totalMessages: int
    deliveryRate: float
    failedMessages: int
    pendingRetry: int
    messagesByChannel: MessagesByChannelDTO
    comparedToPrevious: ComparedToPreviousDTO


# ---------------------------------------------------------------------------
# 2. GET /admin/dashboard/volume
# ---------------------------------------------------------------------------
class VolumePointDTO(BaseModel):

    date: str
    sent: int
    delivered: int
    failed: int


class DashboardVolumeResponseDTO(BaseModel):
    data: List[VolumePointDTO]


# ---------------------------------------------------------------------------
# 3. GET /admin/dashboard/channels
# ---------------------------------------------------------------------------
class ChannelBreakdownItemDTO(BaseModel):
    channel: str
    sent: int
    delivered: int
    failed: int
    deliveryRate: float


class DashboardChannelsResponseDTO(BaseModel):
    channels: List[ChannelBreakdownItemDTO]


# ---------------------------------------------------------------------------
# 4. GET /admin/dashboard/activity
# ---------------------------------------------------------------------------
class ActivityItemDTO(BaseModel):
    id: str
    type: str  
    channel: Optional[str] = None
    tenantName: Optional[str] = None
    message: str
    timestamp: datetime


class DashboardActivityResponseDTO(BaseModel):
    items: List[ActivityItemDTO]


# ---------------------------------------------------------------------------
# 5. GET /admin/dashboard/top-tenants
# ---------------------------------------------------------------------------
class TopTenantItemDTO(BaseModel):
    tenantId: str
    tenantName: str
    totalMessages: int
    deliveryRate: float
    channels: List[str]  

class DashboardTopTenantsResponseDTO(BaseModel):
    items: List[TopTenantItemDTO]


# ---------------------------------------------------------------------------
# 6. GET /admin/dashboard/provider-health
# ---------------------------------------------------------------------------
class ProviderHealthItemDTO(BaseModel):
    providerName: str
    displayName: str
    channel: str
    isActive: bool
    successRate: float
    lastTestAt: Optional[datetime] = None
    lastTestSuccess: Optional[bool] = None
    totalSent: int


class DashboardProviderHealthResponseDTO(BaseModel):
    providers: List[ProviderHealthItemDTO]


# ---------------------------------------------------------------------------
# 7. GET /admin/dashboard/failures
# ---------------------------------------------------------------------------
class TopErrorItemDTO(BaseModel):
    message: str
    count: int


class FailuresResponseDTO(BaseModel):
    total: int
    needsRetry: int
    byChannel: Dict[str, int]
    byProvider: Dict[str, int]
    topErrors: List[TopErrorItemDTO]


# ---------------------------------------------------------------------------
# 8. GET /admin/analytics/sent-messages  (our multi-dimension endpoint)
# ---------------------------------------------------------------------------
class SentMessageRowDTO(BaseModel):
    tenantId: Optional[UUID] = None
    tenantName: Optional[str] = None
    channel: str
    period: str  
    sent: int
    delivered: int
    failed: int
    deliveryRate: float


class SentMessagesResponseDTO(BaseModel):
    rows: List[SentMessageRowDTO]
    total: int
    filtersApplied: Dict[str, Optional[str]]
