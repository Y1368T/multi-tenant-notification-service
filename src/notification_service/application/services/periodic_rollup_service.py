"""
Periodic Message-Count Rollup Service (Redis-backed).

Computes 1-minute message counts (sent, delivered, failed, retried) broken down
by tenant and channel, storing sparse 1-minute buckets in Redis. Coarser granularities
(5m, 30m, 1h) are derived on read by summing 1-minute buckets without querying PostgreSQL.

Memory & Architecture Highlights:
- Option B schema: agg:{tenantId}:1m:{epochMinute} and agg:_all_:1m:{epochMinute}.
- Listpack encoding: 20 hash fields (5 channels x 4 metrics) stay well within
  hash-max-listpack-entries (512) and hash-max-listpack-value (64), measuring ~136 bytes/hash.
- Sparse keys: Keys written ONLY for tenants with activity in that minute.
- Deliberate 1-minute write-visibility safety buffer: Rollup targets [T-2m, T-1m]
  to ensure all in-flight PostgreSQL transactions are committed before rollup.
- 120-minute gap recovery backfill window for service restarts/downtimes.
- Idempotent HSET writes via pipeline, whole-key EXPIRE with 25-hour retention (90,000s).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID


def dt_to_epoch_min(dt: datetime) -> int:
    """Converts a naive (UTC) or UTC-aware datetime to UTC epoch minute."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() // 60)


def epoch_min_to_dt(epoch_min: int) -> datetime:
    """Converts a UTC epoch minute back to naive UTC datetime."""
    return datetime.fromtimestamp(epoch_min * 60, tz=timezone.utc).replace(tzinfo=None)

from redis.asyncio import Redis
from sqlalchemy import DateTime, String, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persistence.models.telegram.telegram_notification import TelegramNotificationModel
from notification_service.infrastructure.persistence.models.telegram.telegram_outbox import TelegramOutboxModel
from notification_service.infrastructure.persistence.models.telegram.telegram_template import TelegramTemplateModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.shared.exceptions.application_exceptions import ValidationError

logger = logging.getLogger(__name__)

DELIVERED_STATUSES = ("sent", "delivered", "read")
FAILED_STATUSES = ("failed", "permanently_failed")

CHANNELS = ("sms", "email", "inapp", "whatsapp", "telegram")
METRICS = ("sent", "delivered", "failed", "retried")

# Channel name -> (OutboxModel, TemplateModel, NotificationModel)
CHANNEL_MODELS = {
    "sms": (SmsOutboxModel, SmsTemplateModel, SMSNotificationModel),
    "email": (EmailOutboxModel, EmailTemplateModel, EmailNotificationModel),
    "inapp": (InAppOutboxModel, InAppTemplateModel, InAppNotificationModel),
    "whatsapp": (WhatsAppOutboxModel, WhatsAppTemplateModel, WhatsAppNotificationModel),
    "telegram": (TelegramOutboxModel, TelegramTemplateModel, TelegramNotificationModel),
}

SUPPORTED_GRANULARITIES = {
    "1m": 1,
    "5m": 5,
    "30m": 30,
    "1h": 60,
}

# 25 hours retention (1,500 minutes) to comfortably serve 24h dashboard queries + 1h buffer
DEFAULT_TTL_SECONDS = 90000

# Up to 2 hours of backfill on service restart/crash recovery
MAX_BACKFILL_MINUTES = 120

LAST_ROLLUP_META_KEY = "agg:_meta_:last_rollup_epoch_min"


class PeriodicMetricsRollupService:
    """
    Scheduled aggregation service that computes 1-minute message metrics
    and provides zero-Postgres granular read path queries from Redis.
    """

    def __init__(
        self,
        uow_factory: Any,
        cache_or_redis: Union[RedisCache, Redis],
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_backfill_minutes: int = MAX_BACKFILL_MINUTES,
    ):
        """
        Initialize the rollup service.

        Args:
            uow_factory: Callable that returns an IUnitOfWork context manager (e.g. lambda: UnitOfWork(database)).
            cache_or_redis: RedisCache instance or direct redis.asyncio.Redis client.
            ttl_seconds: TTL for 1-minute bucket keys (default: 90,000s = 25h).
            max_backfill_minutes: Maximum minutes to backfill on gap recovery (default: 120m).
        """
        self.uow_factory = uow_factory
        if isinstance(cache_or_redis, RedisCache):
            self._redis_cache = cache_or_redis
            self._redis_client = None
        else:
            self._redis_cache = None
            self._redis_client = cache_or_redis

        self.ttl_seconds = ttl_seconds
        self.max_backfill_minutes = max_backfill_minutes

    @property
    def redis(self) -> Redis:
        if self._redis_client is not None:
            return self._redis_client
        return self._redis_cache.client

    def _unioned_outbox_query(self, channels: Optional[List[str]] = None):
        """
        Builds a UNION ALL query across raw outbox tables and notification tables
        for all supported channels (sms, email, inapp, whatsapp, telegram).
        """
        names = channels or list(CHANNEL_MODELS.keys())
        branches = []
        for name in names:
            outbox_model, template_model, notification_model = CHANNEL_MODELS[name]

            # 1. Outbox branch (pending, retrying, failed, or sent messages still in outbox)
            branches.append(
                select(
                    literal(name).label("channel"),
                    outbox_model.createdAt.label("createdAt"),
                    outbox_model.updatedAt.label("updatedAt"),
                    outbox_model.status.label("status"),
                    outbox_model.retryCount.label("retryCount"),
                    outbox_model.lastRetryAt.label("lastRetryAt"),
                    template_model.tenantId.label("tenantId"),
                )
                .select_from(outbox_model)
                .outerjoin(template_model, outbox_model.templateId == template_model.id)
            )

            # 2. Notifications branch (successfully sent/delivered messages)
            branches.append(
                select(
                    literal(name).label("channel"),
                    notification_model.createdAt.label("createdAt"),
                    notification_model.updatedAt.label("updatedAt"),
                    notification_model.status.label("status"),
                    literal(0).label("retryCount"),
                    literal(None).cast(DateTime).label("lastRetryAt"),
                    template_model.tenantId.label("tenantId"),
                )
                .select_from(notification_model)
                .outerjoin(template_model, notification_model.templateId == template_model.id)
            )

        unioned = branches[0].union_all(*branches[1:]) if len(branches) > 1 else branches[0]
        return unioned.subquery()

    # =========================================================================
    # Phase 2: Write Path (The Rollup Job)
    # =========================================================================

    async def run_rollup_cycle(self, now: Optional[datetime] = None) -> int:
        """
        Executes one rollup cycle. Determines the last fully-closed minute with
        a deliberate 1-minute write-visibility buffer, detects any gaps since
        the last successful run (up to max_backfill_minutes), and processes all
        pending 1-minute windows sequentially.

        Returns:
            Number of 1-minute windows rolled up in this cycle.
        """
        current_time = now or datetime.utcnow()
        # Floor to whole minute
        now_floored = current_time.replace(second=0, microsecond=0)

        # Deliberate write-visibility safety buffer:
        # At 10:15:03, target closed window is [10:13:00, 10:14:00).
        # We index the bucket by its start minute (10:13:00).
        # This guarantees database transactions from 10:13:5x have fully committed.
        target_start_time = now_floored - timedelta(minutes=2)
        target_epoch_min = dt_to_epoch_min(target_start_time)

        # Check last processed rollup epoch from Redis
        last_epoch_raw = await self.redis.get(LAST_ROLLUP_META_KEY)
        if last_epoch_raw is not None:
            try:
                last_epoch = int(last_epoch_raw)
            except (ValueError, TypeError):
                last_epoch = target_epoch_min - 1
        else:
            # First execution: only process target_epoch_min
            last_epoch = target_epoch_min - 1

        if target_epoch_min <= last_epoch:
            logger.debug("PeriodicRollup: Window %d already processed (last: %d).", target_epoch_min, last_epoch)
            return 0

        # Gap detection & recovery (capped to max_backfill_minutes)
        start_epoch = max(last_epoch + 1, target_epoch_min - self.max_backfill_minutes)
        epochs_to_process = list(range(start_epoch, target_epoch_min + 1))

        if len(epochs_to_process) > 1:
            logger.info(
                "PeriodicRollup: Gap detected. Backfilling %d missed 1-minute windows (%d to %d).",
                len(epochs_to_process),
                epochs_to_process[0],
                epochs_to_process[-1],
            )

        windows_processed = 0
        for epoch_m in epochs_to_process:
            win_start = epoch_min_to_dt(epoch_m)
            win_end = win_start + timedelta(minutes=1)
            await self._aggregate_and_write_window(win_start, win_end, epoch_m)
            windows_processed += 1

        return windows_processed

    async def _aggregate_and_write_window(self, start_time: datetime, end_time: datetime, epoch_min: int) -> int:
        """
        Queries Postgres for a single closed 1-minute window [start_time, end_time),
        computes sparse active tenant hashes and in-memory global hash, and writes
        them idempotently to Redis in a single pipeline.

        Returns:
            Number of Redis keys written.
        """
        uq = self._unioned_outbox_query()

        # NOTE ON RETRIED COUNT (Phase 2 Step 3):
        # Outbox models update lastRetryAt in-place rather than appending to an audit log.
        # We count rows where lastRetryAt falls within [start_time, end_time).
        # Known accepted limitation: A message retried multiple times within the same
        # 1-minute window is counted once.
        stmt = (
            select(
                uq.c.tenantId,
                uq.c.channel,
                func.count(
                    case(
                        ((uq.c.createdAt >= start_time) & (uq.c.createdAt < end_time), 1),
                        else_=None,
                    )
                ).label("sent"),
                func.count(
                    case(
                        (
                            (uq.c.createdAt >= start_time)
                            & (uq.c.createdAt < end_time)
                            & (uq.c.status.in_(DELIVERED_STATUSES)),
                            1,
                        ),
                        else_=None,
                    )
                ).label("delivered"),
                func.count(
                    case(
                        (
                            (uq.c.createdAt >= start_time)
                            & (uq.c.createdAt < end_time)
                            & (uq.c.status.in_(FAILED_STATUSES)),
                            1,
                        ),
                        else_=None,
                    )
                ).label("failed"),
                func.count(
                    case(
                        (
                            (uq.c.lastRetryAt >= start_time)
                            & (uq.c.lastRetryAt < end_time),
                            1,
                        ),
                        else_=None,
                    )
                ).label("retried"),
            )
            .where(
                ((uq.c.createdAt >= start_time) & (uq.c.createdAt < end_time))
                | ((uq.c.lastRetryAt >= start_time) & (uq.c.lastRetryAt < end_time))
            )
            .group_by(uq.c.tenantId, uq.c.channel)
        )

        async with self.uow_factory() as uow:
            session: AsyncSession = uow.session
            result = await session.execute(stmt)
            rows = result.all()

        # Initialize global aggregator (computed strictly in-memory, 0 extra Postgres queries)
        global_mapping = {f"{ch}_{m}": 0 for ch in CHANNELS for m in METRICS}
        per_tenant_mappings: Dict[str, Dict[str, int]] = {}

        total_activity = 0
        for row in rows:
            tenant_key = str(row.tenantId) if row.tenantId else "unknown"
            if tenant_key not in per_tenant_mappings:
                per_tenant_mappings[tenant_key] = {f"{ch}_{m}": 0 for ch in CHANNELS for m in METRICS}

            ch = row.channel
            sent = int(row.sent or 0)
            delivered = int(row.delivered or 0)
            failed = int(row.failed or 0)
            retried = int(row.retried or 0)

            if f"{ch}_sent" in per_tenant_mappings[tenant_key]:
                per_tenant_mappings[tenant_key][f"{ch}_sent"] += sent
                per_tenant_mappings[tenant_key][f"{ch}_delivered"] += delivered
                per_tenant_mappings[tenant_key][f"{ch}_failed"] += failed
                per_tenant_mappings[tenant_key][f"{ch}_retried"] += retried

                global_mapping[f"{ch}_sent"] += sent
                global_mapping[f"{ch}_delivered"] += delivered
                global_mapping[f"{ch}_failed"] += failed
                global_mapping[f"{ch}_retried"] += retried

                total_activity += (sent + delivered + failed + retried)

        # Prepare pipeline writes
        keys_to_write: Dict[str, Dict[str, str]] = {}

        # 1. Sparse active tenant keys (written only if tenant had activity)
        for tenant_key, mapping in per_tenant_mappings.items():
            k = f"agg:{tenant_key}:1m:{epoch_min}"
            keys_to_write[k] = {field: str(val) for field, val in mapping.items()}

        # 2. In-memory global key agg:_all_:1m:{epochMinute}
        global_key = f"agg:_all_:1m:{epoch_min}"
        keys_to_write[global_key] = {field: str(val) for field, val in global_mapping.items()}

        # Write to Redis via single pipeline (idempotent HSET overwrite + EXPIRE)
        async with self.redis.pipeline(transaction=False) as pipe:
            for key, mapping in keys_to_write.items():
                pipe.hset(key, mapping=mapping)
                pipe.expire(key, self.ttl_seconds)
            pipe.set(LAST_ROLLUP_META_KEY, str(epoch_min))
            await pipe.execute()

        logger.debug(
            "PeriodicRollup: Window %s - %s (epoch %d) written. %d keys (active tenants: %d, activity: %d).",
            start_time.isoformat(),
            end_time.isoformat(),
            epoch_min,
            len(keys_to_write),
            len(per_tenant_mappings),
            total_activity,
        )
        return len(keys_to_write)

    # =========================================================================
    # Phase 3: Read Path (Granular Range Aggregation)
    # =========================================================================

    async def get_periodic_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "1m",
        tenant_id: Optional[Union[str, UUID]] = None,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves message aggregate metrics across requested time range and granularity
        by fetching 1-minute Redis buckets in a single pipelined batch and summing them
        in application memory. Zero PostgreSQL queries.

        Args:
            start_time: Range start (inclusive).
            end_time: Range end (exclusive).
            granularity: One of '1m', '5m', '30m', '1h'.
            tenant_id: Specific tenant ID, or None for system-wide (_all_).
            channel: Specific channel filter ('sms', 'email', 'inapp', 'whatsapp', 'telegram') or None for all.

        Returns:
            Dict containing summary totals, granularity series, and completeness metadata.
        """
        if granularity not in SUPPORTED_GRANULARITIES:
            raise ValidationError(
                message=f"Invalid granularity '{granularity}'. Supported: {', '.join(SUPPORTED_GRANULARITIES.keys())}",
                code="INVALID_GRANULARITY",
            )

        if channel is not None and channel not in CHANNELS:
            raise ValidationError(
                message=f"Invalid channel '{channel}'. Supported: {', '.join(CHANNELS)}",
                code="INVALID_CHANNEL",
            )

        step_minutes = SUPPORTED_GRANULARITIES[granularity]

        # Calculate epoch minute range
        start_epoch = dt_to_epoch_min(start_time)
        end_epoch = dt_to_epoch_min(end_time)

        if end_epoch <= start_epoch:
            return {
                "granularity": granularity,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "channel": channel,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": {"sent": 0, "delivered": 0, "failed": 0, "retried": 0, "by_channel": {}},
                "series": [],
                "metadata": {"expected_1m_buckets": 0, "found_1m_buckets": 0, "missing_1m_buckets": 0, "is_complete": True},
            }

        # Determine Redis key prefix
        if tenant_id:
            key_prefix = f"agg:{str(tenant_id)}:1m:"
        else:
            key_prefix = "agg:_all_:1m:"

        epoch_list = list(range(start_epoch, end_epoch))
        keys = [f"{key_prefix}{m}" for m in epoch_list]

        # Single pipelined round-trip to Redis for all 1-minute bucket keys
        async with self.redis.pipeline(transaction=False) as pipe:
            for k in keys:
                pipe.hgetall(k)
            raw_bucket_hashes = await pipe.execute()

        # Parse buckets into structured minute-level records
        channels_to_read = [channel] if channel else list(CHANNELS)
        found_buckets_count = 0
        parsed_1m_buckets: Dict[int, Dict[str, Any]] = {}

        for idx, epoch_m in enumerate(epoch_list):
            raw_hash = raw_bucket_hashes[idx]
            if raw_hash:
                found_buckets_count += 1

            minute_data: Dict[str, Dict[str, int]] = {}
            for ch in channels_to_read:
                minute_data[ch] = {
                    "sent": int(raw_hash.get(f"{ch}_sent", 0)) if raw_hash else 0,
                    "delivered": int(raw_hash.get(f"{ch}_delivered", 0)) if raw_hash else 0,
                    "failed": int(raw_hash.get(f"{ch}_failed", 0)) if raw_hash else 0,
                    "retried": int(raw_hash.get(f"{ch}_retried", 0)) if raw_hash else 0,
                }
            parsed_1m_buckets[epoch_m] = minute_data

        # Sum 1-minute buckets into requested granularity buckets in application memory
        series: List[Dict[str, Any]] = []
        overall_summary = {"sent": 0, "delivered": 0, "failed": 0, "retried": 0}
        channel_overall = {ch: {"sent": 0, "delivered": 0, "failed": 0, "retried": 0} for ch in channels_to_read}

        curr_bucket_start_epoch = start_epoch
        while curr_bucket_start_epoch < end_epoch:
            curr_bucket_end_epoch = min(curr_bucket_start_epoch + step_minutes, end_epoch)

            b_sent = 0
            b_delivered = 0
            b_failed = 0
            b_retried = 0
            b_channels = {ch: {"sent": 0, "delivered": 0, "failed": 0, "retried": 0} for ch in channels_to_read}

            for m in range(curr_bucket_start_epoch, curr_bucket_end_epoch):
                m_data = parsed_1m_buckets.get(m, {})
                for ch in channels_to_read:
                    ch_metrics = m_data.get(ch, {"sent": 0, "delivered": 0, "failed": 0, "retried": 0})
                    s = ch_metrics["sent"]
                    d = ch_metrics["delivered"]
                    f = ch_metrics["failed"]
                    r = ch_metrics["retried"]

                    b_channels[ch]["sent"] += s
                    b_channels[ch]["delivered"] += d
                    b_channels[ch]["failed"] += f
                    b_channels[ch]["retried"] += r

                    b_sent += s
                    b_delivered += d
                    b_failed += f
                    b_retried += r

                    channel_overall[ch]["sent"] += s
                    channel_overall[ch]["delivered"] += d
                    channel_overall[ch]["failed"] += f
                    channel_overall[ch]["retried"] += r

                    overall_summary["sent"] += s
                    overall_summary["delivered"] += d
                    overall_summary["failed"] += f
                    overall_summary["retried"] += r

            bucket_start_dt = epoch_min_to_dt(curr_bucket_start_epoch)
            bucket_end_dt = epoch_min_to_dt(curr_bucket_end_epoch)

            series.append({
                "bucket_start": bucket_start_dt.isoformat() + "Z",
                "bucket_end": bucket_end_dt.isoformat() + "Z",
                "sent": b_sent,
                "delivered": b_delivered,
                "failed": b_failed,
                "retried": b_retried,
                "by_channel": b_channels,
            })

            curr_bucket_start_epoch = curr_bucket_end_epoch

        total_expected = len(keys)
        missing_count = total_expected - found_buckets_count

        return {
            "granularity": granularity,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "channel": channel,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "summary": {
                **overall_summary,
                "by_channel": channel_overall,
            },
            "series": series,
            "metadata": {
                "expected_1m_buckets": total_expected,
                "found_1m_buckets": found_buckets_count,
                "missing_1m_buckets": missing_count,
                "is_complete": (missing_count == 0),
            },
        }
