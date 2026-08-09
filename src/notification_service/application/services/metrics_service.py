import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func, case, literal
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
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
from notification_service.shared.exceptions.application_exceptions import ValidationError

logger = logging.getLogger(__name__)

DELIVERED_STATUSES = ("sent", "delivered", "read")
FAILED_STATUSES = ("failed", "permanently_failed")

CHANNEL_MODELS = {
    "sms": (SmsOutboxModel, SmsTemplateModel),
    "email": (EmailOutboxModel, EmailTemplateModel),
    "inapp": (InAppOutboxModel, InAppTemplateModel),
    "whatsapp": (WhatsAppOutboxModel, WhatsAppTemplateModel),
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
            outbox_model, template_model = CHANNEL_MODELS[name]
            branches.append(
                select(
                    literal(name).label("channel"),
                    outbox_model.createdAt.label("createdAt"),
                    outbox_model.updatedAt.label("updatedAt"),
                    outbox_model.status.label("status"),
                    outbox_model.retryCount.label("retryCount"),
                    outbox_model.lastErrorMessage.label("lastErrorMessage"),
                    outbox_model.providerAttempted.label("providerAttempted"),
                    template_model.tenantId.label("tenantId"),
                    outbox_model.templateId.label("templateId"),
                    template_model.name.label("templateName"),
                ).select_from(outbox_model).outerjoin(
                    template_model, outbox_model.templateId == template_model.id
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

    async def get_period_totals(
        self, start: datetime, end: Optional[datetime], channel: Optional[str] = None, tenant_id: Optional[UUID] = None
    ) -> Tuple[int, int, int]:
        """Returns (sent, delivered, failed) for a time period using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if end:
                conditions.append(MessageAggregateModel.timeBucket < end)
            if channel:
                conditions.append(MessageAggregateModel.channel == channel)
            if tenant_id:
                conditions.append(MessageAggregateModel.tenantId == str(tenant_id))
                
            stmt = select(
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed")
            ).where(*conditions)
            
            row = (await session.execute(stmt)).one()
            return (int(row.sent or 0), int(row.delivered or 0), int(row.failed or 0))

    async def get_channel_breakdown(
        self, start: datetime, end: Optional[datetime], tenant_id: Optional[UUID] = None
    ) -> Dict[str, Tuple[int, int, int]]:
        """Returns Dict[channel, (sent, delivered, failed)] using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if end:
                conditions.append(MessageAggregateModel.timeBucket < end)
            if tenant_id:
                conditions.append(MessageAggregateModel.tenantId == str(tenant_id))
                
            stmt = select(
                MessageAggregateModel.channel,
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed")
            ).where(*conditions).group_by(MessageAggregateModel.channel)
            
            rows = (await session.execute(stmt)).all()
            return {row.channel: (int(row.sent or 0), int(row.delivered or 0), int(row.failed or 0)) for row in rows}

    async def get_volume_series(
        self, start: datetime, granularity: str, channels: Optional[List[str]] = None, tenant_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Returns volume series using rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start]
            if channels:
                conditions.append(MessageAggregateModel.channel.in_(channels))
            if tenant_id:
                conditions.append(MessageAggregateModel.tenantId == str(tenant_id))
                
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

    async def get_pending_retry_count(self, tenant_id: Optional[UUID] = None) -> int:
        """This queries raw outbox because 'pending' and 'retryCount > 0' are point-in-time state, not historical."""
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            
            conditions = [uq.c.status == "pending", uq.c.retryCount > 0]
            if tenant_id:
                conditions.append(uq.c.tenantId == str(tenant_id))
                
            stmt = select(func.count()).select_from(uq).where(*conditions)
            return (await session.execute(stmt)).scalar() or 0

    async def get_top_errors(
        self, start: datetime, limit: int = 10, channel: Optional[str] = None, tenant_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Queries raw outbox because error messages are high cardinality and not in rollup."""
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            errorLabel = func.coalesce(uq.c.lastErrorMessage, literal("Unknown error"))
            
            conditions = [uq.c.createdAt >= start, uq.c.status.in_(FAILED_STATUSES)]
            if channel:
                conditions.append(uq.c.channel == channel)
            if tenant_id:
                conditions.append(uq.c.tenantId == str(tenant_id))
                
            stmt = select(
                errorLabel.label("message"), func.count().label("count")
            ).where(
                *conditions
            ).group_by(errorLabel).order_by(func.count().desc()).limit(limit)
            
            rows = (await session.execute(stmt)).all()
            return [{"message": row.message, "count": row.count} for row in rows]

    async def get_provider_analytics(
        self, start: datetime, end: Optional[datetime], channel: Optional[str] = None, tenant_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Returns analytics aggregated by provider using the rollup table."""
        async with self.uow:
            session = self._session()
            conditions = [MessageAggregateModel.timeBucket >= start, MessageAggregateModel.provider.isnot(None)]
            if end:
                conditions.append(MessageAggregateModel.timeBucket < end)
            if channel:
                conditions.append(MessageAggregateModel.channel == channel)
            if tenant_id:
                conditions.append(MessageAggregateModel.tenantId == str(tenant_id))
                
            stmt = select(
                MessageAggregateModel.provider.label("providerName"),
                func.sum(MessageAggregateModel.messageCount).label("sent"),
                func.sum(case((MessageAggregateModel.status.in_(DELIVERED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("delivered"),
                func.sum(case((MessageAggregateModel.status.in_(FAILED_STATUSES), MessageAggregateModel.messageCount), else_=0)).label("failed")
            ).where(*conditions).group_by(MessageAggregateModel.provider)
            
            rows = (await session.execute(stmt)).all()
            return [
                {
                    "providerName": row.providerName,
                    "sent": int(row.sent or 0),
                    "delivered": int(row.delivered or 0),
                    "failed": int(row.failed or 0)
                } for row in rows
            ]

    async def get_template_analytics(
        self, start: datetime, end: Optional[datetime], channel: Optional[str] = None, tenant_id: Optional[UUID] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        async with self.uow:
            session = self._session()
            uq = self._unioned_outbox_query()
            
            conditions = [uq.c.createdAt >= start, uq.c.templateId.isnot(None)]
            if end:
                conditions.append(uq.c.createdAt < end)
            if channel:
                conditions.append(uq.c.channel == channel)
            if tenant_id:
                conditions.append(uq.c.tenantId == str(tenant_id))
            
            stmt = select(
                uq.c.templateId.label("templateId"),
                uq.c.templateName.label("templateName"),
                func.count().label("sent"),
                func.sum(case((uq.c.status == "delivered", 1), else_=0)).label("delivered"),
                func.sum(case((uq.c.status == "failed", 1), else_=0)).label("failed"),
            ).select_from(uq).where(*conditions).group_by(
                uq.c.templateId, uq.c.templateName
            ).order_by(
                desc("sent")
            ).limit(limit)
            
            rows = (await session.execute(stmt)).all()
            return [
                {
                    "templateId": row.templateId,
                    "templateName": row.templateName,
                    "sent": int(row.sent or 0),
                    "delivered": int(row.delivered or 0),
                    "failed": int(row.failed or 0)
                }
                for row in rows
            ]

    async def get_activity_feed(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Combine recent outbox events, tenant creations, and user creations into a unified feed."""
        from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
        from notification_service.infrastructure.persistence.models.user.user import UserModel
        
        async with self.uow:
            session = self._session()
            
            # 1. Outbox events
            uq = self._unioned_outbox_query()
            outbox_stmt = select(
                uq.c.id, uq.c.status, uq.c.channel, uq.c.tenantName, uq.c.createdAt
            ).select_from(uq).order_by(desc(uq.c.createdAt)).limit(limit)
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
            if etype == "pending":
                etype = "retry"
            items.append({
                "id": row.id,
                "type": etype,
                "channel": row.channel,
                "tenantName": row.tenantName or "Unknown",
                "message": f"Message {etype} via {row.channel}",
                "timestamp": row.createdAt
            })
            
        for row in tenant_rows:
            items.append({
                "id": row.id,
                "type": "tenant_created",
                "channel": None,
                "tenantName": row.name,
                "message": f"Tenant '{row.name}' was created.",
                "timestamp": row.createdAt
            })
            
        for row in user_rows:
            items.append({
                "id": row.id,
                "type": "user_created",
                "channel": None,
                "tenantName": "System",
                "message": f"User '{row.email}' was provisioned.",
                "timestamp": row.createdAt
            })
            
        # Sort by timestamp desc and take top `limit`
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        return items[:limit]
