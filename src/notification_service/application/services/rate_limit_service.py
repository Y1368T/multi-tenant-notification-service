import logging
import time
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.shared.exceptions.application_exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)

# Per-channel config repo lookup, keyed by channel name.
# Extend this dict as you add channels (whatsapp, telegram, ...).
class RateLimitService:
    def __init__(self, unitOfWork: IUnitOfWork, redis: RedisCache):
        self.unitOfWork = unitOfWork
        self.redis = redis

    async def checkAndIncrement(self, tenantId, tenantPrefix: str, channel: str) -> None:
        """
        Raises RateLimitExceededError if the tenant is over their limit for this channel.
        Increments the counters if allowed. Call this BEFORE routing the message.
        """
        limits = await self._resolveEffectiveLimits(tenantId, channel)

        now = int(time.time())
        windows = {
            "minute": (now // 60, 60, limits["minute"]),
            "hour": (now // 3600, 3600, limits["hour"]),
            "day": (now // 86400, 86400, limits["day"]),
        }

        for windowName, (bucket, ttlSeconds, limit) in windows.items():
            key = f"rate:{tenantId}:{channel}:{windowName}:{bucket}"
            current = await self.redis.increment(key)
            if current == 1:
                # first hit in this bucket -> set expiry so old buckets don't pile up
                await self.redis.client.expire(key, ttlSeconds + 5)
            if current > limit:
                logger.warning(f"Rate limit exceeded: tenant={tenantPrefix} channel={channel} window={windowName} {current}/{limit}")
                raise RateLimitExceededError(str(tenantId), channel, windowName, limit)

    async def _resolveEffectiveLimits(self, tenantId, channel: str) -> dict:
        """
        Resolution rule: per-channel config limits win if an active config exists,
        otherwise fall back to the tenant-wide limits.
        """
        async with self.unitOfWork:
            tenant = await self.unitOfWork.tenants.getById(tenantId)
            channelConfigs = await self._getChannelConfigs(channel, tenantId)

        activeConfig = next((c for c in channelConfigs if c.isActive), None) if channelConfigs else None

        if activeConfig:
            return {
                "minute": activeConfig.rateLimitPerMinute,
                "hour": activeConfig.rateLimitPerHour,
                "day": activeConfig.rateLimitPerDay,
            }
        return {
            "minute": tenant.rateLimitPerMinute,
            "hour": tenant.rateLimitPerHour,
            "day": tenant.rateLimitPerDay,
        }

    async def _getChannelConfigs(self, channel: str, tenantId):
        channel = channel.lower()
        if channel == "sms":
            return await self.unitOfWork.tenantSmsConfigurations.find(lambda t: t.tenantId == tenantId)
        if channel == "email":
            return await self.unitOfWork.tenantEmailConfigurations.find(lambda t: t.tenantId == tenantId)
        if channel == "inapp":
            return await self.unitOfWork.tenantInAppConfigurations.find(lambda t: t.tenantId == tenantId)
        if channel == "whatsapp":
            return await self.unitOfWork.tenantWhatsAppConfigurations.find(lambda t: t.tenantId == tenantId)
        if channel == "telegram":
            return await self.unitOfWork.tenantTelegramConfigurations.find(lambda t: t.tenantId == tenantId)
        return []