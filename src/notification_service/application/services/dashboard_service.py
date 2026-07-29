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
            previousSent, previousDelivered, previousFailed = await self.metrics.get_period_totals(previousSince, since)

            currentRate = _safe_rate(currentDelivered, currentSent)
            previousRate = _safe_rate(previousDelivered, previousSent)

            channelBreakdown = await self.metrics.get_channel_breakdown(since, None)

            async with self.uow:
                session = self.uow.session  # type: ignore[attr-defined]
                totalTenants = (await session.execute(select(func.count()).select_from(TenantModel))).scalar() or 0
                activeTenants = (
                    await session.execute(select(func.count()).select_from(TenantModel).where(TenantModel.isActive.is_(True)))
                ).scalar() or 0

            pendingRetry = await self.metrics.get_pending_retry_count()

            return {
                "totalTenants": totalTenants,
                "activeTenants": activeTenants,
                "totalMessages": currentSent,
                "deliveryRate": currentRate,
                "failedMessages": currentFailed,
                "pendingRetry": pendingRetry,
                "messagesByChannel": {
                    "sms": channelBreakdown.get("sms", (0, 0, 0))[0],
                    "email": channelBreakdown.get("email", (0, 0, 0))[0],
                    "inapp": channelBreakdown.get("inapp", (0, 0, 0))[0],
                    "whatsapp": channelBreakdown.get("whatsapp", (0, 0, 0))[0],
                },
                "comparedToPrevious": {
                    "totalMessages": _format_percent_change(currentSent, previousSent),
                    "deliveryRate": _format_point_change(currentRate, previousRate),
                    "failedMessages": _format_absolute_change(currentFailed, previousFailed),
                },
            }

        return await self._cached(f"stats:{period}", ttlSeconds=30, compute=compute)

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

    # -- 8. GET /admin/analytics/sent-messages -------------------------------

    async def getSentMessages(
        self,
        tenantIds: Optional[List[UUID]] = None,
        channels: Optional[List[str]] = None,
        startDate: Optional[datetime] = None,
        endDate: Optional[datetime] = None,
        granularity: str = "day",
    ) -> dict:
        
        if granularity not in SENT_MESSAGES_GRANULARITY:
            raise ValidationError(
                message=f"Invalid granularity '{granularity}'. Must be one of: {', '.join(SENT_MESSAGES_GRANULARITY)}",
                code="INVALID_GRANULARITY",
            )

        async with self.uow:
            session = self.uow.session  # type: ignore[attr-defined]
            uq = self.metrics._unioned_outbox_query(channels)

            conditions = []
            if tenantIds:
                conditions.append(uq.c.tenantId.in_(tenantIds))
            if startDate is not None:
                conditions.append(uq.c.createdAt >= startDate)
            if endDate is not None:
                conditions.append(uq.c.createdAt < endDate)

            if granularity == "none":
                bucketCol = literal("all").label("bucket")
            else:
                bucketCol = func.date_trunc(granularity, uq.c.createdAt).label("bucket")

            stmt = select(
                uq.c.tenantId,
                uq.c.channel,
                bucketCol,
                func.count().label("sent"),
                func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
            ).where(*conditions).group_by(uq.c.tenantId, uq.c.channel, bucketCol).order_by(bucketCol)

            rows = (await session.execute(stmt)).all()

            tenantIdsInResult = {row.tenantId for row in rows if row.tenantId is not None}
            tenantNames: Dict[UUID, str] = {}
            if tenantIdsInResult:
                tRows = (
                    await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIdsInResult)))
                ).all()
                tenantNames = {r.id: r.name for r in tRows}

            resultRows = []
            grandTotal = 0
            for row in rows:
                sent = row.sent or 0
                delivered = int(row.delivered or 0)
                failed = int(row.failed or 0)
                grandTotal += sent
                bucketLabel = row.bucket if granularity == "none" else row.bucket.isoformat()
                resultRows.append({
                    "tenantId": row.tenantId,
                    "tenantName": tenantNames.get(row.tenantId) if row.tenantId else None,
                    "channel": row.channel,
                    "period": bucketLabel,
                    "sent": sent,
                    "delivered": delivered,
                    "failed": failed,
                    "deliveryRate": _safe_rate(delivered, sent),
                })

            return {
                "rows": resultRows,
                "total": grandTotal,
                "filtersApplied": {
                    "tenantIds": ",".join(str(t) for t in tenantIds) if tenantIds else None,
                    "channels": ",".join(channels) if channels else None,
                    "startDate": startDate.isoformat() if startDate else None,
                    "endDate": endDate.isoformat() if endDate else None,
                    "granularity": granularity,
                },
            }
