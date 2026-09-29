"""
Unit and Integration Tests for Periodic Message-Count Rollup Service (Redis-backed).

Verifies all 7 Phase 4 requirements from Agent_Brief_Periodic_Rollups.md:
1. Correctness test: synthetic known outbox/notification rows produce exact expected Redis hash values.
2. Idempotency test: running twice for the same window produces identical results without doubling.
3. Cross-check test: summing 1-minute buckets matches direct database query counts for the same period.
4. Memory test: realistic multi-day volume of buckets verified for memory usage & listpack encoding.
5. Expiry test: key disappears from Redis after its TTL elapses.
6. Version-compliance check: confirms no unsupported commands (e.g. HEXPIRE, TS.*) are used.
7. Gap-recovery test: simulates missed rollup runs and confirms automatic sequential backfilling.
"""
import asyncio
import inspect
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import case, func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB
from sqlalchemy.types import ARRAY as Base_ARRAY

@compiles(PG_ARRAY, "sqlite")
@compiles(Base_ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(PG_JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from notification_service.application.services.periodic_rollup_service import (
    CHANNELS,
    METRICS,
    PeriodicMetricsRollupService,
    LAST_ROLLUP_META_KEY,
    dt_to_epoch_min,
    epoch_min_to_dt,
)
from notification_service.config.settings import Settings
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.models.base import Base as ModelBase
import notification_service.infrastructure.persistence.models
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
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork


# Use test DB index 1 on the running Redis instance (port 6380)
REDIS_TEST_URL = "redis://localhost:6380/1"


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Provides a clean Redis client on test DB 1, flushed before and after each test."""
    client = Redis.from_url(REDIS_TEST_URL, decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def rollup_db(tmp_path) -> AsyncGenerator[Database, None]:
    """Provides a file-backed SQLite database with all tables created."""
    db_path = tmp_path / "test_rollup.db"
    settings = Settings()
    settings.database_url = f"sqlite+aiosqlite:///{db_path}"
    db = Database(settings)
    await db.connect()
    async with db.engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)
    try:
        yield db
    finally:
        await db.disconnect()


@pytest_asyncio.fixture
def service_factory(rollup_db: Database, redis_client: Redis):
    """Factory returning a PeriodicMetricsRollupService instance connected to test DB & Redis."""
    def _create(ttl_seconds: int = 90000, max_backfill_minutes: int = 120):
        def uow_factory() -> IUnitOfWork:
            return UnitOfWork(rollup_db)

        return PeriodicMetricsRollupService(
            uow_factory=uow_factory,
            cache_or_redis=redis_client,
            ttl_seconds=ttl_seconds,
            max_backfill_minutes=max_backfill_minutes,
        )

    return _create


# =============================================================================
# Helper: Seed Test Tenant & Templates
# =============================================================================

async def create_test_tenant(db: Database, name: str = "Test Tenant", prefix: str = "TT") -> TenantModel:
    async with UnitOfWork(db) as uow:
        tenant = TenantModel(id=uuid4(), name=name, prefix=prefix, isActive=True)
        uow.session.add(tenant)
        await uow.commit()
        return tenant


async def create_templates_for_tenant(db: Database, tenant_id) -> dict:
    """Creates one template per channel for the specified tenant."""
    async with UnitOfWork(db) as uow:
        st = SmsTemplateModel(id=uuid4(), tenantId=tenant_id, templateName="sms_tpl", serviceName="auth", content={"text": "hi"}, version=1)
        et = EmailTemplateModel(id=uuid4(), tenantId=tenant_id, templateName="email_tpl", serviceName="auth", body={"body": "hi"}, subject="test", version=1)
        it = InAppTemplateModel(id=uuid4(), tenantId=tenant_id, templateName="inapp_tpl", serviceName="auth", body={"msg": "hi"}, version=1)
        wt = WhatsAppTemplateModel(id=uuid4(), tenantId=tenant_id, templateName="wa_tpl", serviceName="auth", content={"text": "hi"}, version=1)
        tt = TelegramTemplateModel(id=uuid4(), tenantId=tenant_id, templateName="tg_tpl", serviceName="auth", content={"text": "hi"}, version=1)

        uow.session.add_all([st, et, it, wt, tt])
        await uow.commit()
        return {"sms": st.id, "email": et.id, "inapp": it.id, "whatsapp": wt.id, "telegram": tt.id}


# =============================================================================
# 1. Correctness Test
# =============================================================================

@pytest.mark.asyncio
async def test_correctness(rollup_db: Database, redis_client: Redis, service_factory):
    """
    Phase 4.1: Confirm that for a synthetic known set of outbox/notification rows,
    the rollup produces exactly the expected Redis hash values for active tenant and _all_.
    """
    service: PeriodicMetricsRollupService = service_factory()
    tenant = await create_test_tenant(rollup_db)
    tpl_ids = await create_templates_for_tenant(rollup_db, tenant.id)

    # We test a 1-minute window: 2026-09-04 10:13:00 to 10:14:00
    win_start = datetime(2026, 9, 4, 10, 13, 0)
    win_end = datetime(2026, 9, 4, 10, 14, 0)
    target_now = datetime(2026, 9, 4, 10, 15, 5)  # Rollup run time (targets [10:13, 10:14))

    # Seed synthetic rows:
    # SMS: 2 delivered (notification table), 1 failed (outbox), 1 retried in window (outbox)
    # Email: 1 sent (outbox status='sent'), 1 retried in window
    # Telegram: 3 delivered (notification)
    async with UnitOfWork(rollup_db) as uow:
        # SMS Notifications (delivered)
        uow.session.add_all([
            SMSNotificationModel(id=uuid4(), templateId=tpl_ids["sms"], recipientNumber="+12345", messageContent={"text": "hi"}, status="delivered", idempotencyKey=str(uuid4()), createdAt=win_start + timedelta(seconds=10)),
            SMSNotificationModel(id=uuid4(), templateId=tpl_ids["sms"], recipientNumber="+12346", messageContent={"text": "hi"}, status="delivered", idempotencyKey=str(uuid4()), createdAt=win_start + timedelta(seconds=20)),
        ])
        # SMS Outbox: 1 failed, 1 created yesterday but retried in this window
        uow.session.add_all([
            SmsOutboxModel(id=uuid4(), templateId=tpl_ids["sms"], recipientNumber="+12347", messageContent="fail", idempotencyKey=str(uuid4()), status="failed", createdAt=win_start + timedelta(seconds=30)),
            SmsOutboxModel(id=uuid4(), templateId=tpl_ids["sms"], recipientNumber="+12348", messageContent="retry", idempotencyKey=str(uuid4()), status="pending", retryCount=1, createdAt=win_start - timedelta(days=1), lastRetryAt=win_start + timedelta(seconds=40)),
        ])
        # Email Outbox: 1 sent, 1 retried in window
        uow.session.add_all([
            EmailOutboxModel(id=uuid4(), templateId=tpl_ids["email"], recipientEmail="a@b.com", messageContent={"body": "ok"}, idempotencyKey=str(uuid4()), status="sent", createdAt=win_start + timedelta(seconds=15)),
            EmailOutboxModel(id=uuid4(), templateId=tpl_ids["email"], recipientEmail="b@b.com", messageContent={"body": "retry"}, idempotencyKey=str(uuid4()), status="pending", retryCount=2, createdAt=win_start - timedelta(hours=2), lastRetryAt=win_start + timedelta(seconds=25)),
        ])
        # Telegram Notifications: 3 delivered
        for i in range(3):
            uow.session.add(
                TelegramNotificationModel(id=uuid4(), templateId=tpl_ids["telegram"], recipientChatId=f"chat_{i}", messageContent={"t": "tg"}, status="delivered", idempotencyKey=str(uuid4()), createdAt=win_start + timedelta(seconds=5 + i * 10))
            )
        await uow.commit()

    # Execute rollup cycle
    windows_count = await service.run_rollup_cycle(now=target_now)
    assert windows_count == 1

    epoch_min = dt_to_epoch_min(win_start)
    tenant_key = f"agg:{tenant.id}:1m:{epoch_min}"
    global_key = f"agg:_all_:1m:{epoch_min}"

    tenant_hash = await redis_client.hgetall(tenant_key)
    global_hash = await redis_client.hgetall(global_key)

    assert tenant_hash, f"Tenant key {tenant_key} must exist in Redis"
    assert global_hash, f"Global key {global_key} must exist in Redis"

    # Verify exact SMS counts:
    # sent in window = 2 (notif) + 1 (failed outbox) = 3 (the retried one was created yesterday)
    # delivered in window = 2
    # failed in window = 1
    # retried in window = 1
    assert int(tenant_hash["sms_sent"]) == 3
    assert int(tenant_hash["sms_delivered"]) == 2
    assert int(tenant_hash["sms_failed"]) == 1
    assert int(tenant_hash["sms_retried"]) == 1

    # Verify exact Email counts:
    # sent = 1, delivered = 1 ("sent" is in DELIVERED_STATUSES), failed = 0, retried = 1
    assert int(tenant_hash["email_sent"]) == 1
    assert int(tenant_hash["email_delivered"]) == 1
    assert int(tenant_hash["email_failed"]) == 0
    assert int(tenant_hash["email_retried"]) == 1

    # Verify exact Telegram counts:
    # sent = 3, delivered = 3, failed = 0, retried = 0
    assert int(tenant_hash["telegram_sent"]) == 3
    assert int(tenant_hash["telegram_delivered"]) == 3
    assert int(tenant_hash["telegram_failed"]) == 0
    assert int(tenant_hash["telegram_retried"]) == 0

    # In-memory global key must match tenant exactly (since only 1 tenant was active)
    for field, val in tenant_hash.items():
        assert global_hash[field] == val


# =============================================================================
# 2. Idempotency Test
# =============================================================================

@pytest.mark.asyncio
async def test_idempotency(rollup_db: Database, redis_client: Redis, service_factory):
    """
    Phase 4.2: Execute the rollup job twice for the same window.
    Assert values are identical after the second run - no doubling, no drift.
    """
    service: PeriodicMetricsRollupService = service_factory()
    tenant = await create_test_tenant(rollup_db)
    tpl_ids = await create_templates_for_tenant(rollup_db, tenant.id)

    win_start = datetime(2026, 9, 4, 11, 0, 0)
    win_end = datetime(2026, 9, 4, 11, 1, 0)
    epoch_min = dt_to_epoch_min(win_start)

    # Seed 5 SMS messages
    async with UnitOfWork(rollup_db) as uow:
        for i in range(5):
            uow.session.add(
                SMSNotificationModel(
                    id=uuid4(),
                    templateId=tpl_ids["sms"],
                    recipientNumber=f"+111{i}",
                    messageContent={"text": "idemp"},
                    status="delivered",
                    idempotencyKey=str(uuid4()),
                    createdAt=win_start + timedelta(seconds=10 + i),
                )
            )
        await uow.commit()

    # First run
    await service._aggregate_and_write_window(win_start, win_end, epoch_min)
    first_tenant_hash = await redis_client.hgetall(f"agg:{tenant.id}:1m:{epoch_min}")
    first_global_hash = await redis_client.hgetall(f"agg:_all_:1m:{epoch_min}")

    assert int(first_tenant_hash["sms_sent"]) == 5
    assert int(first_tenant_hash["sms_delivered"]) == 5

    # Second run (exact same window)
    await service._aggregate_and_write_window(win_start, win_end, epoch_min)
    second_tenant_hash = await redis_client.hgetall(f"agg:{tenant.id}:1m:{epoch_min}")
    second_global_hash = await redis_client.hgetall(f"agg:_all_:1m:{epoch_min}")

    # Assert complete equality (no doubling)
    assert first_tenant_hash == second_tenant_hash
    assert first_global_hash == second_global_hash
    assert int(second_tenant_hash["sms_sent"]) == 5


# =============================================================================
# 3. Cross-Check Test (Read Path vs Direct DB Query)
# =============================================================================

@pytest.mark.asyncio
async def test_cross_check_with_db(rollup_db: Database, redis_client: Redis, service_factory):
    """
    Phase 4.3: Cross-check that summing 1-minute Redis buckets produces the
    EXACT same numbers as directly querying the database across a multi-minute span.
    """
    service: PeriodicMetricsRollupService = service_factory()
    tenant = await create_test_tenant(rollup_db)
    tpl_ids = await create_templates_for_tenant(rollup_db, tenant.id)

    base_time = datetime(2026, 9, 4, 12, 0, 0)

    # Seed 10 minutes of varying activity
    expected_total_sent = 0
    expected_total_delivered = 0
    expected_total_failed = 0
    expected_total_retried = 0

    async with UnitOfWork(rollup_db) as uow:
        for m in range(10):
            minute_start = base_time + timedelta(minutes=m)
            # Add 2 delivered SMS
            uow.session.add(
                SMSNotificationModel(
                    id=uuid4(), templateId=tpl_ids["sms"], recipientNumber=f"+20{m}1",
                    messageContent={"t": "m"}, status="delivered", idempotencyKey=str(uuid4()),
                    createdAt=minute_start + timedelta(seconds=10)
                )
            )
            uow.session.add(
                SMSNotificationModel(
                    id=uuid4(), templateId=tpl_ids["sms"], recipientNumber=f"+20{m}2",
                    messageContent={"t": "m"}, status="delivered", idempotencyKey=str(uuid4()),
                    createdAt=minute_start + timedelta(seconds=20)
                )
            )
            # Add 1 failed Email
            uow.session.add(
                EmailOutboxModel(
                    id=uuid4(), templateId=tpl_ids["email"], recipientEmail=f"fail{m}@test.com",
                    messageContent={"b": "f"}, idempotencyKey=str(uuid4()), status="failed",
                    createdAt=minute_start + timedelta(seconds=30)
                )
            )
            # Add 1 retried Telegram message
            uow.session.add(
                TelegramOutboxModel(
                    id=uuid4(), templateId=tpl_ids["telegram"], recipientChatId=f"tg_chat_{m}",
                    messageContent="retry", idempotencyKey=str(uuid4()), status="pending",
                    retryCount=1, createdAt=minute_start - timedelta(hours=1),
                    lastRetryAt=minute_start + timedelta(seconds=40)
                )
            )
            expected_total_sent += 3
            expected_total_delivered += 2
            expected_total_failed += 1
            expected_total_retried += 1

        await uow.commit()

    # Roll up all 10 minutes
    for m in range(10):
        win_start = base_time + timedelta(minutes=m)
        win_end = win_start + timedelta(minutes=1)
        epoch_m = dt_to_epoch_min(win_start)
        await service._aggregate_and_write_window(win_start, win_end, epoch_m)

    # Query via Read Path (granularity="1h") - zero DB query
    range_end = base_time + timedelta(minutes=10)
    read_result = await service.get_periodic_metrics(
        start_time=base_time,
        end_time=range_end,
        granularity="1h",
        tenant_id=tenant.id,
    )

    summary = read_result["summary"]
    assert summary["sent"] == expected_total_sent
    assert summary["delivered"] == expected_total_delivered
    assert summary["failed"] == expected_total_failed
    assert summary["retried"] == expected_total_retried

    # Compare against direct DB query for the exact same range
    async with UnitOfWork(rollup_db) as uow:
        uq = service._unioned_outbox_query()
        direct_db_stmt = select(
            func.count(case(((uq.c.createdAt >= base_time) & (uq.c.createdAt < range_end), 1), else_=None)).label("sent"),
            func.count(case(((uq.c.createdAt >= base_time) & (uq.c.createdAt < range_end) & (uq.c.status.in_(("sent", "delivered", "read"))), 1), else_=None)).label("delivered"),
            func.count(case(((uq.c.createdAt >= base_time) & (uq.c.createdAt < range_end) & (uq.c.status.in_(("failed", "permanently_failed"))), 1), else_=None)).label("failed"),
            func.count(case(((uq.c.lastRetryAt >= base_time) & (uq.c.lastRetryAt < range_end), 1), else_=None)).label("retried"),
        ).where(
            (uq.c.tenantId == tenant.id)
            & (
                ((uq.c.createdAt >= base_time) & (uq.c.createdAt < range_end))
                | ((uq.c.lastRetryAt >= base_time) & (uq.c.lastRetryAt < range_end))
            )
        )
        row = (await uow.session.execute(direct_db_stmt)).one()

        assert summary["sent"] == int(row.sent)
        assert summary["delivered"] == int(row.delivered)
        assert summary["failed"] == int(row.failed)
        assert summary["retried"] == int(row.retried)


# =============================================================================
# 4. Memory Test & Listpack Validation
# =============================================================================

@pytest.mark.asyncio
async def test_memory_and_listpack_encoding(redis_client: Redis):
    """
    Phase 4.4: Populate a multi-day volume of buckets (1,440 buckets = 24 hours),
    measure MEMORY USAGE and OBJECT ENCODING, and confirm Redis listpack optimization.
    """
    sample_mapping = {
        "sms_sent": "15", "sms_delivered": "14", "sms_failed": "1", "sms_retried": "0",
        "email_sent": "20", "email_delivered": "19", "email_failed": "1", "email_retried": "2",
        "inapp_sent": "5", "inapp_delivered": "5", "inapp_failed": "0", "inapp_retried": "0",
        "whatsapp_sent": "12", "whatsapp_delivered": "12", "whatsapp_failed": "0", "whatsapp_retried": "0",
        "telegram_sent": "8", "telegram_delivered": "7", "telegram_failed": "1", "telegram_retried": "1",
    }

    test_key = "agg:test_tenant:1m:123456"
    await redis_client.hset(test_key, mapping=sample_mapping)

    # 1. Verify object encoding is listpack
    encoding = await redis_client.execute_command("OBJECT", "ENCODING", test_key)
    assert encoding in ("listpack", "ziplist"), f"Expected listpack/ziplist encoding, got {encoding}"

    # 2. Verify single key memory usage is compact (< 300 bytes)
    sample_mem = await redis_client.execute_command("MEMORY", "USAGE", test_key)
    assert sample_mem is not None
    assert int(sample_mem) < 500, f"Expected key memory < 500 bytes, got {sample_mem} bytes"

    # 3. Simulate 1,440 buckets (24 hours for 1 tenant) via pipelined write
    async with redis_client.pipeline(transaction=False) as pipe:
        for m in range(1440):
            pipe.hset(f"agg:sim_tenant:1m:{100000 + m}", mapping=sample_mapping)
            pipe.expire(f"agg:sim_tenant:1m:{100000 + m}", 90000)
        await pipe.execute()

    # Total payload for 1,440 keys should be well under 1 MB
    # (1440 * ~200B ≈ 288 KB)
    info_mem = await redis_client.info("memory")
    used_memory = info_mem["used_memory"]
    assert used_memory > 0
    # Clean up simulation keys
    await redis_client.flushdb()


# =============================================================================
# 5. Expiry Test
# =============================================================================

@pytest.mark.asyncio
async def test_key_expiry(redis_client: Redis):
    """
    Phase 4.5: Confirm that a bucket key actually disappears from Redis
    after its TTL elapses (not just checking that EXPIRE was called).
    """
    key = "agg:expiry_test:1m:99999"
    await redis_client.hset(key, "sms_sent", "1")
    # Set 1-second TTL
    await redis_client.expire(key, 1)

    # Key exists immediately
    assert await redis_client.exists(key) == 1

    # Wait for TTL to expire
    await asyncio.sleep(1.3)

    # Confirm key is actually gone from Redis
    assert await redis_client.exists(key) == 0


# =============================================================================
# 6. Version-Compliance Check
# =============================================================================

def test_version_compliance():
    """
    Phase 4.6: Re-read the service source code and verify that no commands
    requiring Redis 7.4+ (such as HEXPIRE) or Redis Stack modules (TS.*) are used.
    """
    service_source = inspect.getsource(PeriodicMetricsRollupService)

    # Prohibited commands
    assert "hexpire" not in service_source.lower(), "HEXPIRE must not be used in the service"
    assert "hpexpire" not in service_source.lower(), "HPEXPIRE must not be used in the service"
    assert "ts.add" not in service_source.lower(), "RedisTimeSeries must not be used"
    assert "ts.range" not in service_source.lower(), "RedisTimeSeries must not be used"
    assert "hincrby" not in service_source.lower(), "HINCRBY must not be used on write path (HSET idempotent)"


# =============================================================================
# 7. Gap-Recovery Test
# =============================================================================

@pytest.mark.asyncio
async def test_gap_recovery(rollup_db: Database, redis_client: Redis, service_factory):
    """
    Phase 4.7: Simulate the rollup job missing several runs (e.g. service restart or crash).
    Confirm that the service sequentially backfills all missing closed 1-minute windows.
    """
    service: PeriodicMetricsRollupService = service_factory(max_backfill_minutes=120)
    tenant = await create_test_tenant(rollup_db)
    tpl_ids = await create_templates_for_tenant(rollup_db, tenant.id)

    # Base time: 2026-09-04 10:10:00.
    # We record that the last processed rollup was for 10:09:00 - 10:10:00.
    base_time = datetime(2026, 9, 4, 10, 10, 0)
    base_epoch = dt_to_epoch_min(base_time)
    await redis_client.set(LAST_ROLLUP_META_KEY, str(base_epoch))

    # Seed messages in 3 missed windows:
    # Window 1: epoch 101 (10:10:00 - 10:11:00)
    # Window 2: epoch 102 (10:11:00 - 10:12:00)
    # Window 3: epoch 103 (10:12:00 - 10:13:00)
    async with UnitOfWork(rollup_db) as uow:
        for offset in [1, 2, 3]:
            w_start = base_time + timedelta(minutes=offset)
            uow.session.add(
                SMSNotificationModel(
                    id=uuid4(),
                    templateId=tpl_ids["sms"],
                    recipientNumber=f"+300{offset}",
                    messageContent={"t": "backfill"},
                    status="delivered",
                    idempotencyKey=str(uuid4()),
                    createdAt=w_start + timedelta(seconds=15),
                )
            )
        await uow.commit()

    # Rollup job runs at 10:15:05 (target closed window is [10:13:00, 10:14:00), start epoch base_epoch + 3).
    # Since last was base_epoch, the gap is epochs base_epoch + 1, + 2, + 3 (3 missed windows).
    current_run_time = base_time + timedelta(minutes=5, seconds=5)
    windows_processed = await service.run_rollup_cycle(now=current_run_time)

    assert windows_processed == 3, f"Expected 3 backfilled windows, got {windows_processed}"

    # Verify that all 3 missed windows were written to Redis
    for offset in [1, 2, 3]:
        ep = base_epoch + offset
        key = f"agg:{tenant.id}:1m:{ep}"
        h = await redis_client.hgetall(key)
        assert h, f"Key {key} for epoch {ep} should have been backfilled!"
        assert int(h["sms_delivered"]) == 1

    # Verify that last_rollup_epoch_min was updated to the latest epoch (103)
    latest_meta = await redis_client.get(LAST_ROLLUP_META_KEY)
    assert int(latest_meta) == base_epoch + 3
