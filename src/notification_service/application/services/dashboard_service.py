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
    "telegram": (TelegramOutboxModel, TelegramTemplateModel),
}

CACHE_PREFIX = "dashboard"


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
    """Relative percent change, e.g. totalMessages '+12%'."""
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    change = ((current - previous) / previous) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{round(change)}%"


def _format_point_change(current: float, previous: float) -> str:
    """Percentage-POINT difference, e.g. deliveryRate 98.2 vs 98.6 -> '-0.4%'.
    Deliberately different math from _format_percent_change: a relative
    percent change of a rate that's already a percentage would be
    confusing (a move from 98% to 99% is "+1 point", not "+1.02%")."""
    diff = round(current - previous, 1)
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff}%"


def _format_absolute_change(current: int, previous: int) -> str:
    """Plain signed integer difference, e.g. failedMessages '+3'."""
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff}"


class DashboardService:
    """Read-only aggregation service for the admin dashboard."""

    def __init__(self, uow: IUnitOfWork, cache: RedisCache):
        self.uow = uow
        self.cache = cache

    # -- internal helpers ---------------------------------------------------

    def _session(self) -> AsyncSession:
        # IUnitOfWork doesn't declare `.session` in its abstract interface
        # (every other service only ever touches repositories), so this is
        # a deliberate, narrow escape hatch used only by read-only
        # reporting queries that need to aggregate across tables the
        # generic repository doesn't know how to join. Must be called
        # inside `async with self.uow:` (see callers below).
        return self.uow.session  # type: ignore[attr-defined]

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

    def _unioned_query(self, channels: Optional[List[str]] = None):
        """SELECT ... UNION ALL ... across the requested channels' outbox
        tables, each LEFT JOINed to its template to recover tenantId.
        Every branch exposes the same columns so every endpoint below can
        filter/group this one shape instead of hand-writing a per-endpoint
        join."""
        names = channels or list(CHANNEL_MODELS.keys())
        branches = []
        for name in names:
            if name not in CHANNEL_MODELS:
                raise ValidationError(
                    message=f"Invalid channel '{name}'. Must be one of: {', '.join(CHANNEL_MODELS)}",
                    code="INVALID_CHANNEL",
                )
            outbox_model, template_model = CHANNEL_MODELS[name]
            branches.append(
                select(
                    literal(name).label("channel"),
                    outbox_model.createdAt.label("createdAt"),
                    outbox_model.updatedAt.label("updatedAt"),
                    outbox_model.status.label("status"),
                    outbox_model.retryCount.label("retryCount"),
                    outbox_model.sentAt.label("sentAt"),
                    outbox_model.lastRetryAt.label("lastRetryAt"),
                    outbox_model.lastErrorMessage.label("lastErrorMessage"),
                    outbox_model.providerAttempted.label("providerAttempted"),
                    template_model.tenantId.label("tenantId"),
                ).select_from(outbox_model).outerjoin(
                    template_model, outbox_model.templateId == template_model.id
                )
            )
        unioned = branches[0].union_all(*branches[1:]) if len(branches) > 1 else branches[0]
        return unioned.subquery()

    # -- 1. GET /admin/dashboard/stats --------------------------------------

    async def getStats(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            delta = PERIOD_TO_DELTA[period]
            previousSince = since - delta

            async with self.uow:
                session = self._session()
                uq = self._unioned_query()

                def periodTotals(start: datetime, end: Optional[datetime]):
                    conditions = [uq.c.createdAt >= start]
                    if end is not None:
                        conditions.append(uq.c.createdAt < end)
                    return select(
                        func.count().label("sent"),
                        func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                        func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                    ).where(*conditions)

                currentRow = (await session.execute(periodTotals(since, None))).one()
                previousRow = (await session.execute(periodTotals(previousSince, since))).one()

                currentSent = currentRow.sent or 0
                currentDelivered = int(currentRow.delivered or 0)
                currentFailed = int(currentRow.failed or 0)
                currentRate = _safe_rate(currentDelivered, currentSent)

                previousSent = previousRow.sent or 0
                previousDelivered = int(previousRow.delivered or 0)
                previousFailed = int(previousRow.failed or 0)
                previousRate = _safe_rate(previousDelivered, previousSent)

                perChannelStmt = select(
                    uq.c.channel, func.count().label("sent")
                ).where(uq.c.createdAt >= since).group_by(uq.c.channel)
                perChannelRows = {row.channel: row.sent for row in (await session.execute(perChannelStmt)).all()}

                totalTenants = (await session.execute(select(func.count()).select_from(TenantModel))).scalar() or 0
                activeTenants = (
                    await session.execute(select(func.count()).select_from(TenantModel).where(TenantModel.isActive.is_(True)))
                ).scalar() or 0

                # Current backlog snapshot - intentionally NOT period-scoped,
                # since it answers "how big is the retry queue right now",
                # not a historical count.
                pendingRetryStmt = select(func.count()).select_from(uq).where(
                    uq.c.status == "pending", uq.c.retryCount > 0
                )
                pendingRetry = (await session.execute(pendingRetryStmt)).scalar() or 0

                return {
                    "totalTenants": totalTenants,
                    "activeTenants": activeTenants,
                    "totalMessages": currentSent,
                    "deliveryRate": currentRate,
                    "failedMessages": currentFailed,
                    "pendingRetry": pendingRetry,
                    "messagesByChannel": {
                        "sms": perChannelRows.get("sms", 0),
                        "email": perChannelRows.get("email", 0),
                        "inapp": perChannelRows.get("inapp", 0),
                        "whatsapp": perChannelRows.get("whatsapp", 0),
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
            channels = [channel] if channel else None

            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)

                bucket = func.date_trunc(granularity, uq.c.createdAt).label("bucket")
                stmt = select(
                    bucket,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(uq.c.createdAt >= since).group_by(bucket).order_by(bucket)

                rows = (await session.execute(stmt)).all()
                data = [
                    {
                        "date": row.bucket.isoformat(),
                        "sent": row.sent or 0,
                        "delivered": int(row.delivered or 0),
                        "failed": int(row.failed or 0),
                    }
                    for row in rows
                ]
                return {"data": data}

        return await self._cached(f"volume:{period}:{granularity}:{channel or 'all'}", ttlSeconds=60, compute=compute)

    # -- 3. GET /admin/dashboard/channels ------------------------------------

    async def getChannelBreakdown(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()
                stmt = select(
                    uq.c.channel,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(uq.c.createdAt >= since).group_by(uq.c.channel)
                rows = {row.channel: row for row in (await session.execute(stmt)).all()}

                channels = []
                for name in CHANNEL_MODELS:
                    row = rows.get(name)
                    sent = row.sent if row else 0
                    delivered = int(row.delivered or 0) if row else 0
                    failed = int(row.failed or 0) if row else 0
                    channels.append({
                        "channel": name,
                        "sent": sent,
                        "delivered": delivered,
                        "failed": failed,
                        "deliveryRate": _safe_rate(delivered, sent),
                    })
                return {"channels": channels}

        return await self._cached(f"channels:{period}", ttlSeconds=30, compute=compute)
                    
    # -- 4. GET /admin/dashboard/activity -------------------------------------

    async def getActivity(self, limit: int = 20) -> dict:
        
        async def compute() -> dict:
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()

                # Final-state events: only rows that have actually resolved
                # (delivered or failed) - a still-"pending" row hasn't done
                # anything yet worth reporting.
                finalStateStmt = select(
                    uq.c.channel, uq.c.status, uq.c.sentAt, uq.c.updatedAt,
                    uq.c.lastErrorMessage, uq.c.tenantId,
                ).where(uq.c.status.in_(DELIVERED_STATUSES + FAILED_STATUSES)).order_by(
                    uq.c.updatedAt.desc()
                ).limit(limit)
                finalStateRows = (await session.execute(finalStateStmt)).all()

                # Retry events: any row that has ever been retried, timed
                # at its most recent retry.
                retryStmt = select(
                    uq.c.channel, uq.c.lastRetryAt, uq.c.tenantId,
                ).where(uq.c.lastRetryAt.isnot(None)).order_by(uq.c.lastRetryAt.desc()).limit(limit)
                retryRows = (await session.execute(retryStmt)).all()

                tenantCreatedStmt = select(
                    TenantModel.id, TenantModel.name, TenantModel.createdAt
                ).order_by(TenantModel.createdAt.desc()).limit(limit)
                tenantCreatedRows = (await session.execute(tenantCreatedStmt)).all()

                tenantIds = {r.tenantId for r in finalStateRows if r.tenantId} | {r.tenantId for r in retryRows if r.tenantId}
                tenantNames: Dict[UUID, str] = {}
                if tenantIds:
                    tRows = (
                        await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIds)))
                    ).all()
                    tenantNames = {r.id: r.name for r in tRows}

                items = []
                for row in finalStateRows:
                    success = row.status in DELIVERED_STATUSES
                    tenantName = tenantNames.get(row.tenantId) if row.tenantId else None
                    timestamp = row.sentAt if success and row.sentAt else row.updatedAt
                    detail = f": {row.lastErrorMessage}" if not success and row.lastErrorMessage else ""
                    items.append({
                        "id": f"{row.channel}-final-{timestamp.isoformat()}-{tenantName or 'unknown'}",
                        "type": "delivered" if success else "failed",
                        "channel": row.channel,
                        "tenantName": tenantName,
                        "message": (
                            f"{row.channel.upper()} delivered" if success else f"{row.channel.upper()} delivery failed{detail}"
                        ) + (f" for {tenantName}" if tenantName else ""),
                        "timestamp": timestamp,
                    })

                for row in retryRows:
                    tenantName = tenantNames.get(row.tenantId) if row.tenantId else None
                    items.append({
                        "id": f"{row.channel}-retry-{row.lastRetryAt.isoformat()}-{tenantName or 'unknown'}",
                        "type": "retry",
                        "channel": row.channel,
                        "tenantName": tenantName,
                        "message": f"Retry attempted for {row.channel.upper()} message" + (f" ({tenantName})" if tenantName else ""),
                        "timestamp": row.lastRetryAt,
                    })

                for row in tenantCreatedRows:
                    items.append({
                        "id": f"tenant-{row.id}",
                        "type": "tenant_created",
                        "channel": None,
                        "tenantName": row.name,
                        "message": f"Tenant '{row.name}' created",
                        "timestamp": row.createdAt,
                    })

                items.sort(key=lambda i: i["timestamp"], reverse=True)
                return {"items": items[:limit]}

        return await self._cached(f"activity:{limit}", ttlSeconds=15, compute=compute)
 
    # -- 5. GET /admin/dashboard/top-tenants ----------------------------------

    async def getTopTenants(self, limit: int = 5, period: str = "7d") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()
                stmt = select(
                    uq.c.tenantId,
                    uq.c.channel,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                ).where(uq.c.createdAt >= since, uq.c.tenantId.isnot(None)).group_by(uq.c.tenantId, uq.c.channel)
                rows = (await session.execute(stmt)).all()

                perTenant: Dict[UUID, Dict[str, Any]] = {}
                for row in rows:
                    entry = perTenant.setdefault(row.tenantId, {"sent": 0, "delivered": 0, "channels": set()})
                    entry["sent"] += row.sent or 0
                    entry["delivered"] += int(row.delivered or 0)
                    if (row.sent or 0) > 0:
                        entry["channels"].add(row.channel)

                ranked = sorted(perTenant.items(), key=lambda kv: kv[1]["sent"], reverse=True)[:limit]
                if not ranked:
                    return {"items": []}

                tenantIds = [tid for tid, _ in ranked]
                tenantRows = (
                    await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIds)))
                ).all()
                tenantNames = {r.id: r.name for r in tenantRows}

                items = []
                for tenantId, agg in ranked:
                    if tenantId not in tenantNames:
                        continue  # tenant deleted after messages were sent; skip rather than fabricate a name
                    items.append({
                        "tenantId": str(tenantId),
                        "tenantName": tenantNames[tenantId],
                        "totalMessages": agg["sent"],
                        "deliveryRate": _safe_rate(agg["delivered"], agg["sent"]),
                        "channels": sorted(agg["channels"]),
                    })
                return {"items": items}

        return await self._cached(f"top-tenants:{limit}:{period}", ttlSeconds=60, compute=compute)

    # -- 6. GET /admin/dashboard/provider-health -----------------------------

    async def getProviderHealth(self) -> dict:
        async def compute() -> dict:
            async with self.uow:
                session = self._session()
                providers = (await session.execute(select(ProviderModel))).scalars().all()

                uq = self._unioned_query()
                perfStmt = select(
                    uq.c.channel,
                    uq.c.providerAttempted,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                ).group_by(uq.c.channel, uq.c.providerAttempted)
                perf = {(row.channel, row.providerAttempted): row for row in (await session.execute(perfStmt)).all()}

                items = []
                for provider in providers:
                    row = perf.get((provider.channel, provider.providerName))
                    sent = row.sent if row else 0
                    delivered = int(row.delivered or 0) if row else 0
                    items.append({
                        "providerName": provider.providerName,
                        "displayName": provider.displayName,
                        "channel": provider.channel,
                        "isActive": provider.isActive,
                        "successRate": _safe_rate(delivered, sent),
                        "lastTestAt": getattr(provider, "lastTestedAt", None),
                        "lastTestSuccess": getattr(provider, "lastTestSuccess", None),
                        "totalSent": sent,
                    })
                return {"providers": items}

        return await self._cached("provider-health", ttlSeconds=30, compute=compute)

    # -- 7. GET /admin/dashboard/failures ------------------------------------

    async def getFailures(self, period: str = "24h") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()

                totalStmt = select(func.count()).select_from(uq).where(
                    uq.c.createdAt >= since, uq.c.status.in_(FAILED_STATUSES)
                )
                total = (await session.execute(totalStmt)).scalar() or 0

                needsRetryStmt = select(func.count()).select_from(uq).where(
                    uq.c.status == "pending", uq.c.retryCount > 0
                )
                needsRetry = (await session.execute(needsRetryStmt)).scalar() or 0

                byChannelStmt = select(uq.c.channel, func.count()).where(
                    uq.c.createdAt >= since, uq.c.status.in_(FAILED_STATUSES)
                ).group_by(uq.c.channel)
                byChannel = {row[0]: row[1] for row in (await session.execute(byChannelStmt)).all()}

                byProviderStmt = select(uq.c.providerAttempted, func.count()).where(
                    uq.c.createdAt >= since, uq.c.status.in_(FAILED_STATUSES), uq.c.providerAttempted.isnot(None)
                ).group_by(uq.c.providerAttempted)
                byProvider = {row[0]: row[1] for row in (await session.execute(byProviderStmt)).all()}

                
                errorLabel = func.coalesce(uq.c.lastErrorMessage, literal("Unknown error"))
                topErrorsStmt = select(
                    errorLabel.label("message"), func.count().label("count")
                ).where(
                    uq.c.createdAt >= since, uq.c.status.in_(FAILED_STATUSES)
                ).group_by(errorLabel).order_by(func.count().desc()).limit(10)
                topErrors = [
                    {"message": row.message, "count": row.count}
                    for row in (await session.execute(topErrorsStmt)).all()
                ]

                return {
                    "total": total,
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
            session = self._session()
            uq = self._unioned_query(channels)

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
