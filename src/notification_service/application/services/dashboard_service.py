import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.shared.exceptions.application_exceptions import ValidationError

logger = logging.getLogger(__name__)

DELIVERED_STATUSES = ("sent", "delivered", "read")
FAILED_STATUSES = ("failed", "permanently_failed")


PERIOD_TO_DELTA = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

VOLUME_GRANULARITY_TO_TRUNC = {"hour": "hour", "day": "day", "week": "week"}
SENT_MESSAGES_GRANULARITY = ("day", "week", "month", "none")

# channel name -> (OutboxModel, TemplateModel)
CHANNEL_MODELS = {
    "sms": (SmsOutboxModel, SmsTemplateModel),
    "email": (EmailOutboxModel, EmailTemplateModel),
    "inapp": (InAppOutboxModel, InAppTemplateModel),
    "whatsapp": (WhatsAppOutboxModel, WhatsAppTemplateModel),
    # NOTE: no "telegram" entry - TelegramOutboxModel/TelegramTemplateModel
    # don't exist yet. Telegram currently has a provider + channel handler
    # (see infrastructure/providers/telegram/) but no dedicated outbox/
    # template persistence table, unlike sms/email/inapp/whatsapp. Adding
    # a channel here requires an actual table with the same shape (status,
    # retryCount, sentAt, lastRetryAt, lastErrorMessage, providerAttempted,
    # templateId) to union against - see GUIDE.md "Adding a new channel"
    # for the checklist once that table exists.
}

CACHE_PREFIX = "dashboard"


from notification_service.application.services.metrics_service import MetricsService

def _period_since(period: str) -> datetime:
    delta = PERIOD_TO_DELTA.get(period)
    if delta is None:
        raise ValidationError(
            message=f"Invalid period '{period}'. Must be one of: {', '.join(PERIOD_TO_DELTA)}",
            code="INVALID_PERIOD",
        )
    return datetime.utcnow() - delta


def _safe_rate(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _format_percent_change(current: float, previous: float) -> str:
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    change = ((current - previous) / previous) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{round(change)}%"


def _format_point_change(current: float, previous: float) -> str:
    diff = round(current - previous, 1)
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff}%"


def _format_absolute_change(current: int, previous: int) -> str:
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff}"


class DashboardService:
    """Read-only aggregation service for the admin dashboard."""

    def __init__(self, uow: IUnitOfWork, cache: RedisCache):
        self.uow = uow
        self.cache = cache
        self.metrics = MetricsService(uow)

    async def _cached(self, key: str, ttlSeconds: int, compute: Callable[[], Coroutine[Any, Any, dict]]) -> dict:
        cacheKey = f"{CACHE_PREFIX}:{key}"
        try:
            cached = await self.cache.get(cacheKey)
            if cached is not None:
                return cached
        except Exception:
            logger.warning("Dashboard cache read failed for key '%s'; falling back to live query.", cacheKey)

        result = await compute()

        try:
            await self.cache.set(cacheKey, result, expire=ttlSeconds)
        except Exception:
            logger.warning("Dashboard cache write failed for key '%s'.", cacheKey)

        return result

    # -- 1. GET /admin/dashboard/stats --------------------------------------

    async def getStats(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            delta = PERIOD_TO_DELTA[period]
            previousSince = since - delta

            currentSent, currentDelivered, currentFailed = await self.metrics.get_period_totals(since, None)
    async def getStats(self, period: str = "24h", tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            since = _period_since(period)

            # previous period delta
            delta = datetime.utcnow() - since
            prev_since = since - delta
            
            # total / active tenants (only calculate if tenant_id is not provided, since a tenant dashboard doesn't need "totalTenants")
            totalTenants = 0
            activeTenants = 0
            if not tenant_id:
                async with self.uow:
                    session = self.uow.session  # type: ignore[attr-defined]
                    totalTenants = (await session.execute(select(func.count()).select_from(TenantModel))).scalar() or 0
                    
                    # active tenants in period
                    uq = self.metrics._unioned_outbox_query()
                    activeTenantsStmt = select(func.count(uq.c.tenantId.distinct())).where(uq.c.createdAt >= since)
                    activeTenants = (await session.execute(activeTenantsStmt)).scalar() or 0

            # current period totals
            sent, delivered, failed = await self.metrics.get_period_totals(since, None, tenant_id=tenant_id)
            # pending retry
            needsRetry = await self.metrics.get_pending_retry_count(tenant_id=tenant_id)
            
            # messages by channel
            breakdown = await self.metrics.get_channel_breakdown(since, None, tenant_id=tenant_id)
            byChannel = {channel: (s + d + f) for channel, (s, d, f) in breakdown.items()}

            # previous period totals
            prev_sent, prev_delivered, prev_failed = await self.metrics.get_period_totals(prev_since, since, tenant_id=tenant_id)

            curr_rate = _safe_rate(delivered, sent)
            prev_rate = _safe_rate(prev_delivered, prev_sent)

            return {
                "totalTenants": totalTenants,
                "activeTenants": activeTenants,
                "totalMessages": sent,
                "deliveryRate": curr_rate,
                "failedMessages": failed,
                "pendingRetry": needsRetry,
                "messagesByChannel": byChannel,
                "comparedToPrevious": {
                    "totalMessages": _format_percent_change(sent, prev_sent),
                    "deliveryRate": _format_point_change(curr_rate, prev_rate),
                    "failedMessages": _format_absolute_change(failed, prev_failed),
                }
            }

        cache_key = f"stats:{period}" if not tenant_id else f"stats:{period}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=30, compute=compute)

    # -- 2. GET /admin/dashboard/volume ------------------------------------- 

    async def getVolume(self, period: str = "7d", granularity: str = "day", channel: Optional[str] = None) -> dict:
        async def compute() -> dict:
            if granularity not in VOLUME_GRANULARITY_TO_TRUNC:
                raise ValidationError(
                    message=f"Invalid granularity '{granularity}'. Must be one of: {', '.join(VOLUME_GRANULARITY_TO_TRUNC)}",
                    code="INVALID_GRANULARITY",
                )
            since = _period_since(period)
            channels_list = [channel] if channel else None
            data = await self.metrics.get_volume_series(since, granularity, channels_list)
            return {"data": data}

        return await self._cached(f"volume:{period}:{granularity}:{channel or 'all'}", ttlSeconds=60, compute=compute)

    # -- 3. GET /admin/dashboard/channels ------------------------------------

    async def getChannelBreakdown(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            breakdown = await self.metrics.get_channel_breakdown(since, None)
            channels = []
            for name in CHANNEL_MODELS:
                sent, delivered, failed = breakdown.get(name, (0, 0, 0))
                channels.append({
                    "channel": name,
                    "sent": sent,
                    "delivered": delivered,
                    "failed": failed,
                    "deliveryRate": _safe_rate(delivered, sent),
                })
            return {"channels": channels}

        return await self._cached(f"channels:{period}", ttlSeconds=30, compute=compute)
                    

    # -- 5. GET /admin/dashboard/top-tenants ----------------------------------

    async def getTopTenants(self, limit: int = 5, period: str = "7d") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            items = await self.metrics.get_top_tenants(since, limit)
            for item in items:
                item["deliveryRate"] = _safe_rate(item["delivered"], item["totalMessages"])
                del item["delivered"]
            return {"items": items}

        return await self._cached(f"top-tenants:{limit}:{period}", ttlSeconds=60, compute=compute)


    # -- 6. GET /admin/dashboard/provider-health -----------------------------

    async def getProviderHealth(self) -> dict:
        async def compute() -> dict:
            items = await self.metrics.get_provider_health()
            for item in items:
                item["successRate"] = _safe_rate(item["delivered"], item["totalSent"])
                del item["delivered"]
            return {"providers": items}

        return await self._cached("provider-health", ttlSeconds=30, compute=compute)

    # -- 7. GET /admin/dashboard/activity ------------------------------------

    async def getActivityFeed(self, limit: int = 20) -> dict:
        async def compute() -> dict:
            items = await self.metrics.get_activity_feed(limit=limit)
            return {"items": items}

        return await self._cached(f"activity-feed:{limit}", ttlSeconds=30, compute=compute)
    # -- 7. GET /admin/dashboard/failures ------------------------------------

    async def getFailures(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            _, _, total_failed = await self.metrics.get_period_totals(since, None)
            needsRetry = await self.metrics.get_pending_retry_count()
            
            # For failures, we still need raw outbox query for 'byProvider' and 'topErrors' 
            # as they require granular fields (lastErrorMessage, and provider filtered by failure).
            # Wait, the rollup table HAS provider and status. So we can use the rollup table for `byChannel` and `byProvider`!
            breakdown = await self.metrics.get_channel_breakdown(since, None)
            byChannel = {channel: failed for channel, (_, _, failed) in breakdown.items() if failed > 0}
            
            # For byProvider, we need a small custom query or method. Let's just use raw outbox for now 
            # to match the old logic without modifying MetricsService further, OR add it to MetricsService.
            # Actually, `get_top_errors` is already in MetricsService.
            # Let's just run the remaining raw queries using MetricsService `_unioned_outbox_query`? No, DashboardService shouldn't.
            
            # Let's add `byProvider` logic to MetricsService? Or just fall back to raw outbox here?
            # I will just write the raw query here for byProvider for speed since MetricsService is for dashboard main stats.
            # No, I should use `MetricsService`. Let me modify it slightly here by instantiating raw outbox.
            async with self.uow:
                session = self.uow.session  # type: ignore[attr-defined]
                uq = self.metrics._unioned_outbox_query()
                
                byProviderStmt = select(uq.c.providerAttempted, func.count()).where(
                    uq.c.createdAt >= since, uq.c.status.in_(FAILED_STATUSES), uq.c.providerAttempted.isnot(None)
                ).group_by(uq.c.providerAttempted)
                byProvider = {row[0]: row[1] for row in (await session.execute(byProviderStmt)).all()}

            topErrors = await self.metrics.get_top_errors(since, 10)

            return {
                "total": total_failed,
                "needsRetry": needsRetry,
                "byChannel": byChannel,
                "byProvider": byProvider,
                "topErrors": topErrors,
            }

        return await self._cached(f"failures:{period}", ttlSeconds=30, compute=compute)

    # -- Analytics Suite -----------------------------------------------------

    async def getAnalyticsOverview(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            sent, delivered, failed = await self.metrics.get_period_totals(startDate, endDate, channel=channel, tenant_id=tenant_id)
            return {
                "totalSent": sent,
                "totalDelivered": delivered,
                "totalFailed": failed,
                "deliveryRate": _safe_rate(delivered, sent)
            }
        
        cache_key = f"analytics:overview:{startDate.isoformat()}:{endDate.isoformat()}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsVolume(self, startDate: datetime, endDate: datetime, granularity: str, channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            series = await self.metrics.get_volume_series(startDate, granularity, channels=channels, tenant_id=tenant_id)
            return {"data": series}
            
        cache_key = f"analytics:volume:{startDate.isoformat()}:{granularity}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsFunnel(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            sent, delivered, failed = await self.metrics.get_period_totals(startDate, endDate, channel=channel, tenant_id=tenant_id)
            return {
                "sent": sent,
                "delivered": delivered,
                "failed": failed
            }
            
        cache_key = f"analytics:funnel:{startDate.isoformat()}:{endDate.isoformat()}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsTenants(self, startDate: datetime, endDate: datetime, sortBy: str = "volume", limit: int = 50) -> dict:
        async def compute() -> dict:
            # We already have `get_top_tenants` which sorts by volume. 
            items = await self.metrics.get_top_tenants(startDate, limit)
            for item in items:
                item["deliveryRate"] = _safe_rate(item["delivered"], item["totalMessages"])
                
            if sortBy == "deliveryRate":
                items.sort(key=lambda x: x["deliveryRate"], reverse=True)
            elif sortBy == "failedCount":
                items.sort(key=lambda x: (x["totalMessages"] - x["delivered"]), reverse=True)
                
            return {"items": items}
            
        cache_key = f"analytics:tenants:{startDate.isoformat()}:{sortBy}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsChannels(self, startDate: datetime, endDate: datetime) -> dict:
        async def compute() -> dict:
            breakdown = await self.metrics.get_channel_breakdown(startDate, endDate)
            channels = []
            for channel, (sent, delivered, failed) in breakdown.items():
                channels.append({
                    "channel": channel,
                    "sent": sent,
                    "delivered": delivered,
                    "failed": failed,
                    "deliveryRate": _safe_rate(delivered, sent)
                })
            return {"channels": channels}
            
        cache_key = f"analytics:channels:{startDate.isoformat()}:{endDate.isoformat()}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsProviders(self, startDate: datetime, endDate: datetime) -> dict:
        async def compute() -> dict:
            providers = await self.metrics.get_provider_analytics(startDate, endDate)
            for provider in providers:
                provider["deliveryRate"] = _safe_rate(provider["delivered"], provider["sent"])
            return {"providers": providers}
            
        cache_key = f"analytics:providers:{startDate.isoformat()}:{endDate.isoformat()}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsErrors(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None, limit: int = 10) -> dict:
        async def compute() -> dict:
            topErrors = await self.metrics.get_top_errors(startDate, limit, channel=channel, tenant_id=tenant_id)
            return {"errors": topErrors}
            
        cache_key = f"analytics:errors:{startDate.isoformat()}:{channel}:{tenant_id}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsTemplates(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None, limit: int = 50) -> dict:
        async def compute() -> dict:
            templates = await self.metrics.get_template_analytics(startDate, endDate, channel=channel, tenant_id=tenant_id, limit=limit)
            for tmpl in templates:
                tmpl["deliveryRate"] = _safe_rate(tmpl["delivered"], tmpl["sent"])
            return {"templates": templates}
            
        cache_key = f"analytics:templates:{startDate.isoformat()}:{channel}:{tenant_id}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)
