import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.application.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

class MetricsRollupProcessor:
    """
    Background service that aggregates outbox message counts into the 
    message_aggregates_hourly table for the dashboard.
    """
    
    def __init__(self, database: Database, poll_interval_seconds: int = 300):
        self.database = database
        self.poll_interval = poll_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background processing loop."""
        if self._running:
            logger.warning("MetricsRollupProcessor is already running.")
            return

        self._running = True
        logger.info(f"MetricsRollupProcessor started. Poll interval: {self.poll_interval}s")
        
        # Give the main app a moment to start up before running the first cycle
        await asyncio.sleep(5)
        
        # Run a 30-day backfill exactly once on startup
        try:
            logger.info("MetricsRollupProcessor: Running startup backfill for the last 30 days...")
            now = datetime.utcnow()
            start_time = now - timedelta(days=30)
            
            uow = UnitOfWork(self.database)
            metrics_service = MetricsService(uow)
            rows_upserted = await metrics_service.populate_rollup_table(start_time, now)
            logger.info(f"MetricsRollupProcessor: Startup backfill complete. Upserted {rows_upserted} buckets.")
        except Exception as e:
            logger.error(f"Error during metrics rollup startup backfill: {str(e)}")
        
        while self._running:
            try:
                await self._process_cycle()
            except asyncio.CancelledError:
                logger.info("MetricsRollupProcessor loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Unexpected error in MetricsRollupProcessor: {str(e)}")
            
            if self._running:
                await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the background processing loop."""
        if not self._running:
            return
            
        logger.info("MetricsRollupProcessor stopping...")
        self._running = False
        if self._task:
            self._task.cancel()

    async def _process_cycle(self):
        """Execute one aggregation cycle."""
        try:
            # Create a short-lived UOW for this specific cycle
            uow = UnitOfWork(self.database)
            metrics_service = MetricsService(uow)
            
            # We look back over the last 24 hours to ensure any delayed deliveries are caught 
            # and their buckets are correctly updated. Postgres UPSERT will handle it efficiently.
            now = datetime.utcnow()
            start_time = now - timedelta(hours=24)
            
            logger.debug(f"MetricsRollupProcessor running aggregation from {start_time.isoformat()} to {now.isoformat()}")
            
            rows_upserted = await metrics_service.populate_rollup_table(start_time, now)
            
            if rows_upserted > 0:
                logger.info(f"MetricsRollupProcessor: Upserted {rows_upserted} rollup buckets.")
                
        except Exception as e:
            logger.error(f"Error during metrics rollup aggregation cycle: {str(e)}")
