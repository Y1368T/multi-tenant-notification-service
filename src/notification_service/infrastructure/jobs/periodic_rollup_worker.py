"""
Periodic Rollup Worker.

Background task running once per minute to aggregate message metrics into Redis
via PeriodicMetricsRollupService.
"""
import asyncio
import logging
from typing import Optional, Union
from datetime import datetime

from redis.asyncio import Redis

from notification_service.application.services.periodic_rollup_service import PeriodicMetricsRollupService
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class PeriodicRollupWorker:
    """
    Scheduled background worker that executes the 1-minute rollup job
    every 60 seconds with backfill support.
    """

    def __init__(
        self,
        database: Database,
        cache_or_redis: Union[RedisCache, Redis],
        poll_interval_seconds: int = 60,
    ):
        self.database = database
        self.cache_or_redis = cache_or_redis
        self.poll_interval = poll_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

        def uow_factory():
            return UnitOfWork(self.database)

        self.service = PeriodicMetricsRollupService(
            uow_factory=uow_factory,
            cache_or_redis=cache_or_redis,
        )

    async def start(self):
        """Start the background processing loop."""
        if self._running:
            logger.warning("PeriodicRollupWorker is already running.")
            return

        self._running = True
        logger.info("PeriodicRollupWorker started. Interval: %ds", self.poll_interval)

        # Brief delay to allow db and redis connections to settle on startup
        await asyncio.sleep(2)

        while self._running:
            try:
                windows = await self.service.run_rollup_cycle()
                if windows > 0:
                    logger.debug("PeriodicRollupWorker completed %d rollup window(s).", windows)
            except asyncio.CancelledError:
                logger.info("PeriodicRollupWorker loop cancelled.")
                break
            except Exception as e:
                logger.exception("Unexpected error in PeriodicRollupWorker cycle: %s", str(e))

            if self._running:
                # Sleep to next cycle
                try:
                    await asyncio.sleep(self.poll_interval)
                except asyncio.CancelledError:
                    break

    def stop(self):
        """Stop the background processing loop."""
        if not self._running:
            return

        logger.info("PeriodicRollupWorker stopping...")
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
