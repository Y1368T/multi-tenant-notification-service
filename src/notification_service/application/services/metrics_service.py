import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func, case, literal, String
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.persistence.models.message_aggregate import MessageAggregateModel
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_outbox import WhatsAppOutboxModel
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_template import WhatsAppTemplateModel
from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel
from notification_service.infrastructure.persistence.models.whatsapp.whatsapp_notification import WhatsAppNotificationModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
from notification_service.shared.exceptions.application_exceptions import ValidationError

logger = logging.getLogger(__name__)

DELIVERED_STATUSES = ("sent", "delivered", "read")
FAILED_STATUSES = ("failed", "permanently_failed")

CHANNEL_MODELS = {
    "sms": (SmsOutboxModel, SmsTemplateModel, SMSNotificationModel),
    "email": (EmailOutboxModel, EmailTemplateModel, EmailNotificationModel),
    "inapp": (InAppOutboxModel, InAppTemplateModel, InAppNotificationModel),
    "whatsapp": (WhatsAppOutboxModel, WhatsAppTemplateModel, WhatsAppNotificationModel),
}

class MetricsService:
    """Service to handle core message metrics calculations using the Rollup Table."""

    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def _session(self) -> AsyncSession:
        return self.uow.session  # type: ignore[attr-defined]

    def _unioned_outbox_query(self, channels: Optional[List[str]] = None):
        """Builds a UNION ALL query across raw outbox tables. Used for populating rollups and top errors."""
        names = channels or list(CHANNEL_MODELS.keys())
        branches = []
        for name in names:
            outbox_model, template_model, notification_model = CHANNEL_MODELS[name]
            
            # 1. Outbox branch (pending/failed messages)
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
                ).select_from(outbox_model).outerjoin(
                    template_model, outbox_model.templateId == template_model.id
                )
            )
            
            # 2. Notifications branch (successfully sent messages)
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
                ).select_from(notification_model).outerjoin(
                    template_model, notification_model.templateId == template_model.id
                )
            )
        unioned = branches[0].union_all(*branches[1:]) if len(branches) > 1 else branches[0]
        return unioned.subquery()

    async def populate_rollup_table(self, start_time: datetime, end_time: datetime) -> int:
        """
        Reads from raw outbox tables and aggregates counts into `message_aggregates_hourly`.
        This would typically be called by a background Celery worker or cron job.
        """
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            
            # Truncate to hour
            bucket_col = func.date_trunc('hour', uq.c.createdAt).label('bucket')
            
            # Note: We group by everything needed for the rollup
            # For status, we will map to 'delivered', 'failed', 'pending' for simplicity in rollup?
            # Or keep raw status. Let's keep raw status to avoid losing info.
            stmt = select(
                bucket_col,
                uq.c.tenantId,
                uq.c.channel,
                uq.c.providerAttempted.label("provider"),
                uq.c.status,
                func.count().label("msg_count")
            ).where(
                uq.c.createdAt >= start_time,
                uq.c.createdAt < end_time
            ).group_by(
                bucket_col, uq.c.tenantId, uq.c.channel, uq.c.providerAttempted, uq.c.status
            )
            
            rows = (await session.execute(stmt)).all()
            if not rows:
                return 0
                
            # Upsert into rollup table
            for row in rows:
                if row.bucket is None: continue
                # We use postgresql insert with on_conflict_do_update
                insert_stmt = insert(MessageAggregateModel).values(
                    id=uuid4(),
                    timeBucket=row.bucket,
                    tenantId=row.tenantId,
                    channel=row.channel,
                    provider=row.provider,
                    status=row.status,
                    messageCount=row.msg_count
                )
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['timeBucket', 'tenantId', 'channel', 'provider', 'status'],
                    set_=dict(messageCount=insert_stmt.excluded.messageCount)
                )
                await session.execute(upsert_stmt)
                
            await session.commit()
            return len(rows)

    # --- Dashboard Data Access Methods (Reading from Rollup) ---

    async def get_period_totals(self, start: datetime, end: Optional[datetime]) -> Tuple[int, int, int]:
        """Returns (sent, delivered, failed) for a time period using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if end:
                conditions.append(MessageAggregateModel.timeBucket < end)
                
            stmt = select(
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed")
            ).where(*conditions)
            
            row = (await session.execute(stmt)).one()
            return (int(row.sent or 0), int(row.delivered or 0), int(row.failed or 0))

    async def get_channel_breakdown(self, start: datetime, end: Optional[datetime]) -> Dict[str, Tuple[int, int, int]]:
        """Returns Dict[channel, (sent, delivered, failed)] using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if end:
                conditions.append(MessageAggregateModel.timeBucket < end)
                
            stmt = select(
                MessageAggregateModel.channel,
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed")
            ).where(*conditions).group_by(MessageAggregateModel.channel)
            
            rows = (await session.execute(stmt)).all()
            return {row.channel: (int(row.sent or 0), int(row.delivered or 0), int(row.failed or 0)) for row in rows}

    async def get_volume_series(self, start: datetime, granularity: str, channels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Returns volume series using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if channels:
                conditions.append(MessageAggregateModel.channel.in_(channels))
                
            bucket = func.date_trunc(granularity, MessageAggregateModel.timeBucket).label("bucket")
            stmt = select(
                bucket,
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed"),
            ).where(*conditions).group_by(bucket).order_by(bucket)
            
            rows = (await session.execute(stmt)).all()
            return [
                {
                    "date": row.bucket.isoformat(),
                    "sent": int(row.sent or 0),
                    "delivered": int(row.delivered or 0),
                    "failed": int(row.failed or 0),
                }
                for row in rows
            ]

    async def get_top_tenants(self, start: datetime, limit: int) -> List[Dict[str, Any]]:
        """Returns top tenants using rollup table, solving N+1 memory bloat."""
        async with self.uow:
            session = self._session()
            # Step 1: Get top N tenant IDs
            topStmt = select(
                MessageAggregateModel.tenantId,
                func.sum(MessageAggregateModel.messageCount).label("sent")
            ).where(
                MessageAggregateModel.timeBucket >= start,
                MessageAggregateModel.tenantId.isnot(None)
            ).group_by(MessageAggregateModel.tenantId).order_by(func.sum(MessageAggregateModel.messageCount).desc()).limit(limit)
            
            topRows = (await session.execute(topStmt)).all()
            if not topRows:
                return []
                
            tenantIds = [row.tenantId for row in topRows]
            
            # Step 2: Get detailed breakdown for top N
            detailStmt = select(
                MessageAggregateModel.tenantId,
                MessageAggregateModel.channel,
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
            ).where(
                MessageAggregateModel.timeBucket >= start,
                MessageAggregateModel.tenantId.in_(tenantIds)
            ).group_by(MessageAggregateModel.tenantId, MessageAggregateModel.channel)
            
            detailRows = (await session.execute(detailStmt)).all()
            
            perTenant: Dict[UUID, Dict[str, Any]] = {}
            for row in detailRows:
                entry = perTenant.setdefault(row.tenantId, {"sent": 0, "delivered": 0, "channels": set()})
                entry["sent"] += int(row.sent or 0)
                entry["delivered"] += int(row.delivered or 0)
                if int(row.sent or 0) > 0:
                    entry["channels"].add(row.channel)

            # Fetch tenant names
            tenantRows = (await session.execute(select(TenantModel.id, TenantModel.name).where(TenantModel.id.in_(tenantIds)))).all()
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
                    "delivered": agg["delivered"],
                    "channels": sorted(agg["channels"]),
                })
            return items

    async def get_provider_health(self) -> List[Dict[str, Any]]:
        """Returns provider health using rollup table (avoiding full outbox table scan!)."""
        async with self.uow:
            session = self._session()
            providers = (await session.execute(select(ProviderModel))).scalars().all()
            
            # Now queries the small rollup table instead of massive outbox table!
            stmt = select(
                MessageAggregateModel.channel,
                MessageAggregateModel.provider,
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered")
            ).where(MessageAggregateModel.provider.isnot(None)).group_by(MessageAggregateModel.channel, MessageAggregateModel.provider)
            
            perfRows = (await session.execute(stmt)).all()
            perf = {(row.channel, row.provider): row for row in perfRows}
            
            items = []
            for provider in providers:
                row = perf.get((provider.channel, provider.providerName))
                sent = int(row.sent or 0) if row else 0
                delivered = int(row.delivered or 0) if row else 0
                items.append({
                    "providerName": provider.providerName,
                    "displayName": provider.displayName,
                    "channel": provider.channel,
                    "isActive": provider.isActive,
                    "lastTestAt": getattr(provider, "lastTestedAt", None),
                    "lastTestSuccess": getattr(provider, "lastTestSuccess", None),
                    "totalSent": sent,
                    "delivered": delivered
                })
            return items

    async def get_pending_retry_count(self) -> int:
        """This queries raw outbox because 'pending' and 'retryCount > 0' are point-in-time state, not historical."""
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            stmt = select(func.count()).select_from(uq).where(
                uq.c.status == "pending", uq.c.retryCount > 0
            )
            return (await session.execute(stmt)).scalar() or 0

    async def get_top_errors(self, start: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """Queries raw outbox because error messages are high cardinality and not in rollup."""
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            errorLabel = func.coalesce(uq.c.lastErrorMessage, literal("Unknown error"))
            stmt = select(
                errorLabel.label("message"), func.count().label("count")
            ).where(
                uq.c.createdAt >= start, uq.c.status.in_(FAILED_STATUSES)
            ).group_by(errorLabel).order_by(func.count().desc()).limit(limit)
            
            rows = (await session.execute(stmt)).all()
            return [{"message": row.message, "count": row.count} for row in rows]
