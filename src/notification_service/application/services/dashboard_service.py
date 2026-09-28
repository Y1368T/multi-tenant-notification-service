import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import String, case, desc, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persistence.models.telegram.telegram_notification import TelegramNotificationModel
from notification_service.infrastructure.persistence.models.telegram.telegram_outbox import TelegramOutboxModel
from notification_service.infrastructure.persistence.models.telegram.telegram_template import TelegramTemplateModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.application.services.periodic_rollup_service import PeriodicMetricsRollupService
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

# Channel name -> (OutboxModel, TemplateModel, NotificationModel)
CHANNEL_MODELS = {
    "sms": (SmsOutboxModel, SmsTemplateModel, SMSNotificationModel),
    "email": (EmailOutboxModel, EmailTemplateModel, EmailNotificationModel),
    "inapp": (InAppOutboxModel, InAppTemplateModel, InAppNotificationModel),
    "whatsapp": (WhatsAppOutboxModel, WhatsAppTemplateModel, WhatsAppNotificationModel),
    "telegram": (TelegramOutboxModel, TelegramTemplateModel, TelegramNotificationModel),
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

    def __init__(self, uow: IUnitOfWork, cache: Optional[RedisCache] = None):
        self.uow = uow
        self.cache = cache
        self.rollup_service = PeriodicMetricsRollupService(
            uow_factory=lambda: self.uow,
            cache_or_redis=cache,
        ) if cache else None

    def _session(self) -> AsyncSession:
        return self.uow.session  # type: ignore[attr-defined]

    async def _cached(self, key: str, ttlSeconds: int, compute: Callable[[], Coroutine[Any, Any, dict]]) -> dict:
        cacheKey = f"{CACHE_PREFIX}:{key}"
        if self.cache:
            try:
                cached = await self.cache.get(cacheKey)
                if cached is not None:
                    return cached
            except Exception:
                logger.warning("Dashboard cache read failed for key '%s'; falling back to live query.", cacheKey)

        result = await compute()

        if self.cache:
            try:
                await self.cache.set(cacheKey, result, expire=ttlSeconds)
            except Exception:
                logger.warning("Dashboard cache write failed for key '%s'.", cacheKey)

        return result

    def _unioned_query(self, channels: Optional[List[str]] = None):
        """
        Builds a UNION ALL query across outbox (pending/failed/retrying) and notification
        (sent/delivered) tables for each supported channel.
        """
        names = channels or list(CHANNEL_MODELS.keys())
        branches = []
        for name in names:
            if name not in CHANNEL_MODELS:
                raise ValidationError(
                    message=f"Invalid channel '{name}'. Must be one of: {', '.join(CHANNEL_MODELS)}",
                    code="INVALID_CHANNEL",
                )
            outbox_model, template_model, notification_model = CHANNEL_MODELS[name]

            # 1. Outbox branch (pending / failed / retrying)
            branches.append(
                select(
                    literal(name).label("channel"),
                    outbox_model.createdAt.label("createdAt"),
                    outbox_model.updatedAt.label("updatedAt"),
                    outbox_model.status.label("status"),
                    outbox_model.retryCount.label("retryCount"),
                    outbox_model.lastErrorMessage.label("lastErrorMessage"),
                    outbox_model.providerAttempted.cast(String).label("providerAttempted"),
                    template_model.tenantId.label("tenantId"),
                    outbox_model.templateId.label("templateId"),
                    template_model.name.label("templateName"),
                ).select_from(outbox_model).outerjoin(
                    template_model, outbox_model.templateId == template_model.id
                )
            )

            # 2. Notifications branch (sent / delivered / read)
            branches.append(
                select(
                    literal(name).label("channel"),
                    notification_model.createdAt.label("createdAt"),
                    notification_model.updatedAt.label("updatedAt"),
                    notification_model.status.label("status"),
                    literal(0).label("retryCount"),
                    literal(None).cast(String).label("lastErrorMessage"),
                    literal(None).cast(String).label("providerAttempted"),
                    template_model.tenantId.label("tenantId"),
                    notification_model.templateId.label("templateId"),
                    template_model.name.label("templateName"),
                ).select_from(notification_model).outerjoin(
                    template_model, notification_model.templateId == template_model.id
                )
            )

        unioned = branches[0].union_all(*branches[1:]) if len(branches) > 1 else branches[0]
        return unioned.subquery()

    async def getPeriodicRollupMetrics(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "1m",
        tenant_id: Optional[Union[str, UUID]] = None,
        channel: Optional[str] = None,
    ) -> dict:
        """
        Retrieves message metrics aggregated from 1-minute Redis rollups across
        multiple granularities (1m, 5m, 30m, 1h) without querying PostgreSQL.
        """
        if not self.rollup_service:
            raise ValidationError(
                message="Redis cache is required for periodic rollup metrics.",
                code="REDIS_REQUIRED",
            )
        return await self.rollup_service.get_periodic_metrics(
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,
            tenant_id=tenant_id,
            channel=channel,
        )

    # -- 1. GET /admin/dashboard/stats --------------------------------------

    async def getStats(self, period: str = "24h", tenant_id: Optional[UUID] = None) -> dict:
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
                    if tenant_id:
                        conditions.append(uq.c.tenantId == tenant_id)
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

                perChannelConditions = [uq.c.createdAt >= since]
                if tenant_id:
                    perChannelConditions.append(uq.c.tenantId == tenant_id)
                perChannelStmt = select(
                    uq.c.channel, func.count().label("sent")
                ).where(*perChannelConditions).group_by(uq.c.channel)
                perChannelRows = {row.channel: row.sent for row in (await session.execute(perChannelStmt)).all()}

                totalTenants = 0
                activeTenants = 0
                if not tenant_id:
                    totalTenants = (await session.execute(select(func.count()).select_from(TenantModel))).scalar() or 0
                    activeTenants = (
                        await session.execute(select(func.count()).select_from(TenantModel).where(TenantModel.isActive.is_(True)))
                    ).scalar() or 0

                pendingRetryConditions = [uq.c.status == "pending", uq.c.retryCount > 0]
                if tenant_id:
                    pendingRetryConditions.append(uq.c.tenantId == tenant_id)
                pendingRetryStmt = select(func.count()).select_from(uq).where(*pendingRetryConditions)
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
                        "telegram": perChannelRows.get("telegram", 0),
                    },
                    "comparedToPrevious": {
                        "totalMessages": _format_percent_change(currentSent, previousSent),
                        "deliveryRate": _format_point_change(currentRate, previousRate),
                        "failedMessages": _format_absolute_change(currentFailed, previousFailed),
                    },
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

    # -- 5. GET /admin/dashboard/top-tenants ----------------------------------

    async def getTopTenants(self, limit: int = 5, period: str = "7d") -> dict:
        async def compute() -> dict:
            since = _period_since(period)
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()

                topTenantsStmt = select(
                    uq.c.tenantId,
                    func.count().label("sent")
                ).where(
                    uq.c.createdAt >= since,
                    uq.c.tenantId.isnot(None)
                ).group_by(uq.c.tenantId).order_by(func.count().desc()).limit(limit)

                topTenantRows = (await session.execute(topTenantsStmt)).all()
                if not topTenantRows:
                    return {"items": []}

                tenantIds = [row.tenantId for row in topTenantRows]

                stmt = select(
                    uq.c.tenantId,
                    uq.c.channel,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                ).where(
                    uq.c.createdAt >= since,
                    uq.c.tenantId.in_(tenantIds)
                ).group_by(uq.c.tenantId, uq.c.channel)

                rows = (await session.execute(stmt)).all()

                perTenant: Dict[UUID, Dict[str, Any]] = {}
                for row in rows:
                    entry = perTenant.setdefault(row.tenantId, {"sent": 0, "delivered": 0, "channels": set()})
                    entry["sent"] += row.sent or 0
                    entry["delivered"] += int(row.delivered or 0)
                    if (row.sent or 0) > 0:
                        entry["channels"].add(row.channel)

                tenantRows = (
                    await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIds)))
                ).all()
                tenantNames = {r.id: r.name for r in tenantRows}

                items = []
                for tid in tenantIds:
                    if tid not in tenantNames or tid not in perTenant:
                        continue
                    agg = perTenant[tid]
                    items.append({
                        "tenantId": str(tid),
                        "tenantName": tenantNames[tid],
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
                ).where(uq.c.providerAttempted.isnot(None)).group_by(uq.c.channel, uq.c.providerAttempted)
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

    # -- 7. GET /admin/dashboard/activity ------------------------------------

    async def getActivityFeed(self, limit: int = 20) -> dict:
        async def compute() -> dict:
            async with self.uow:
                session = self._session()

                # 1. Outbox events
                uq = self._unioned_query()
                outbox_stmt = select(
                    uq.c.channel, uq.c.status, uq.c.createdAt
                ).order_by(desc(uq.c.createdAt)).limit(limit)
                outbox_rows = (await session.execute(outbox_stmt)).all()

                # 2. Tenant creations
                tenant_stmt = select(
                    TenantModel.id, TenantModel.name, TenantModel.createdAt
                ).order_by(desc(TenantModel.createdAt)).limit(limit)
                tenant_rows = (await session.execute(tenant_stmt)).all()

                # 3. User creations
                user_stmt = select(
                    UserModel.id, UserModel.email, UserModel.createdAt
                ).order_by(desc(UserModel.createdAt)).limit(limit)
                user_rows = (await session.execute(user_stmt)).all()

            items = []
            for row in outbox_rows:
                etype = row.status
                items.append({
                    "id": str(UUID(int=0)),
                    "type": etype,
                    "channel": row.channel,
                    "tenantName": "Tenant",
                    "message": f"Message {etype} via {row.channel}",
                    "timestamp": row.createdAt,
                })

            for row in tenant_rows:
                items.append({
                    "id": str(row.id),
                    "type": "tenant_created",
                    "channel": None,
                    "tenantName": row.name,
                    "message": f"Tenant '{row.name}' was created.",
                    "timestamp": row.createdAt,
                })

            for row in user_rows:
                items.append({
                    "id": str(row.id),
                    "type": "user_created",
                    "channel": None,
                    "tenantName": "System",
                    "message": f"User '{row.email}' was provisioned.",
                    "timestamp": row.createdAt,
                })

            items.sort(key=lambda x: x["timestamp"], reverse=True)
            return {"items": items[:limit]}

        return await self._cached(f"activity-feed:{limit}", ttlSeconds=30, compute=compute)

    # -- 8. GET /admin/dashboard/failures ------------------------------------

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

    # -- 9. GET /admin/analytics/sent-messages -------------------------------

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

    # -- Analytics Suite -----------------------------------------------------

    async def getAnalyticsOverview(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)
                conditions = [uq.c.createdAt >= startDate, uq.c.createdAt < endDate]
                if tenant_id:
                    conditions.append(uq.c.tenantId == tenant_id)
                stmt = select(
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(*conditions)
                row = (await session.execute(stmt)).one()
                sent = row.sent or 0
                delivered = int(row.delivered or 0)
                failed = int(row.failed or 0)
                return {
                    "totalSent": sent,
                    "totalDelivered": delivered,
                    "totalFailed": failed,
                    "deliveryRate": _safe_rate(delivered, sent),
                }

        cache_key = f"analytics:overview:{startDate.isoformat()}:{endDate.isoformat()}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsVolume(self, startDate: datetime, endDate: datetime, granularity: str = "day", channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)
                conditions = [uq.c.createdAt >= startDate, uq.c.createdAt < endDate]
                if tenant_id:
                    conditions.append(uq.c.tenantId == tenant_id)
                bucket = func.date_trunc(granularity, uq.c.createdAt).label("bucket")
                stmt = select(
                    bucket,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(*conditions).group_by(bucket).order_by(bucket)

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

        cache_key = f"analytics:volume:{startDate.isoformat()}:{granularity}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsFunnel(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)
                conditions = [uq.c.createdAt >= startDate, uq.c.createdAt < endDate]
                if tenant_id:
                    conditions.append(uq.c.tenantId == tenant_id)
                stmt = select(
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(*conditions)
                row = (await session.execute(stmt)).one()
                return {
                    "sent": row.sent or 0,
                    "delivered": int(row.delivered or 0),
                    "failed": int(row.failed or 0),
                }

        cache_key = f"analytics:funnel:{startDate.isoformat()}:{endDate.isoformat()}:{channel}:{tenant_id}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsTenants(self, startDate: datetime, endDate: datetime, sortBy: str = "volume", limit: int = 50) -> dict:
        async def compute() -> dict:
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()
                stmt = select(
                    uq.c.tenantId,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                ).where(
                    uq.c.createdAt >= startDate,
                    uq.c.createdAt < endDate,
                    uq.c.tenantId.isnot(None),
                ).group_by(uq.c.tenantId)
                rows = (await session.execute(stmt)).all()
                tenantIds = [row.tenantId for row in rows]
                tenantNames = {}
                if tenantIds:
                    tRows = (await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIds)))).all()
                    tenantNames = {r.id: r.name for r in tRows}

                items = []
                for row in rows:
                    sent = row.sent or 0
                    delivered = int(row.delivered or 0)
                    items.append({
                        "tenantId": str(row.tenantId),
                        "tenantName": tenantNames.get(row.tenantId, "Unknown"),
                        "totalMessages": sent,
                        "delivered": delivered,
                        "deliveryRate": _safe_rate(delivered, sent),
                    })

                if sortBy == "deliveryRate":
                    items.sort(key=lambda x: x["deliveryRate"], reverse=True)
                elif sortBy == "failedCount":
                    items.sort(key=lambda x: (x["totalMessages"] - x["delivered"]), reverse=True)
                else:
                    items.sort(key=lambda x: x["totalMessages"], reverse=True)

                return {"items": items[:limit]}

        cache_key = f"analytics:tenants:{startDate.isoformat()}:{sortBy}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsChannels(self, startDate: datetime, endDate: datetime) -> dict:
        async def compute() -> dict:
            async with self.uow:
                session = self._session()
                uq = self._unioned_query()
                stmt = select(
                    uq.c.channel,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                    func.sum(case((uq.c.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed"),
                ).where(uq.c.createdAt >= startDate, uq.c.createdAt < endDate).group_by(uq.c.channel)
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

        cache_key = f"analytics:channels:{startDate.isoformat()}:{endDate.isoformat()}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsProviders(self, startDate: datetime, endDate: datetime) -> dict:
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
                ).where(
                    uq.c.createdAt >= startDate,
                    uq.c.createdAt < endDate,
                    uq.c.providerAttempted.isnot(None),
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
                        "sent": sent,
                        "delivered": delivered,
                        "deliveryRate": _safe_rate(delivered, sent),
                    })
                return {"providers": items}

        cache_key = f"analytics:providers:{startDate.isoformat()}:{endDate.isoformat()}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsErrors(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None, limit: int = 10) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)
                errorLabel = func.coalesce(uq.c.lastErrorMessage, literal("Unknown error"))
                conditions = [uq.c.createdAt >= startDate, uq.c.createdAt < endDate, uq.c.status.in_(FAILED_STATUSES)]
                if tenant_id:
                    conditions.append(uq.c.tenantId == tenant_id)
                stmt = select(
                    errorLabel.label("message"), func.count().label("count")
                ).where(*conditions).group_by(errorLabel).order_by(func.count().desc()).limit(limit)
                rows = (await session.execute(stmt)).all()
                return {"errors": [{"message": row.message, "count": row.count} for row in rows]}

        cache_key = f"analytics:errors:{startDate.isoformat()}:{channel}:{tenant_id}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)

    async def getAnalyticsTemplates(self, startDate: datetime, endDate: datetime, channel: Optional[str] = None, tenant_id: Optional[UUID] = None, limit: int = 50) -> dict:
        async def compute() -> dict:
            channels = [channel] if channel else None
            async with self.uow:
                session = self._session()
                uq = self._unioned_query(channels)
                conditions = [uq.c.createdAt >= startDate, uq.c.createdAt < endDate]
                if tenant_id:
                    conditions.append(uq.c.tenantId == tenant_id)
                stmt = select(
                    uq.c.channel,
                    func.count().label("sent"),
                    func.sum(case((uq.c.status.in_(DELIVERED_STATUSES), 1), else_=0)).label("delivered"),
                ).where(*conditions).group_by(uq.c.channel).limit(limit)
                rows = (await session.execute(stmt)).all()
                templates = []
                for row in rows:
                    sent = row.sent or 0
                    delivered = int(row.delivered or 0)
                    templates.append({
                        "channel": row.channel,
                        "sent": sent,
                        "delivered": delivered,
                        "deliveryRate": _safe_rate(delivered, sent),
                    })
                return {"templates": templates}

        cache_key = f"analytics:templates:{startDate.isoformat()}:{channel}:{tenant_id}:{limit}"
        return await self._cached(cache_key, ttlSeconds=60, compute=compute)
