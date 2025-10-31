"""Redis cache implementation using aioredis."""
import json
import logging
from typing import Any, Optional
from redis.asyncio import Redis
from notification_service.domain.interfaces.cache import ICachedRepository

logger = logging.getLogger(__name__)


class RedisCache(ICachedRepository):
    """Redis cache implementation with async support."""
    
    def __init__(self, redis_url: str):
        """Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self._client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = Redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis cache disconnected")
    
    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from the cache by key.
        
        Args:
            key: The cache key.
            
        Returns:
            Cached value (deserialized from JSON), or None if not found.
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, return as string
                return value
        except Exception as e:
            logger.error(f"Error getting key '{key}' from cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set an item in the cache.
        
        Args:
            key: The cache key.
            value: The value to cache (will be serialized to JSON).
            expire: Expiration time in seconds.
        """
        try:
            # Serialize value to JSON if it's not a string
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value, default=str)
            
            if expire:
                await self.client.setex(key, expire, serialized_value)
            else:
                await self.client.set(key, serialized_value)
                
            logger.debug(f"Set cache key '{key}' with expiry {expire}s")
        except Exception as e:
            logger.error(f"Error setting key '{key}' in cache: {e}")
            raise
    
    async def delete(self, key: str) -> None:
        """Delete an item from the cache by key.
        
        Args:
            key: The cache key.
        """
        try:
            await self.client.delete(key)
            logger.debug(f"Deleted cache key '{key}'")
        except Exception as e:
            logger.error(f"Error deleting key '{key}' from cache: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.
        
        Args:
            key: The cache key.
            
        Returns:
            True if the key exists, False otherwise.
        """
        try:
            result = await self.client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking existence of key '{key}': {e}")
            return False
    
    async def get_expiry_time(self, key: str) -> Optional[int]:
        """Get the expiration time for a cache key.
        
        Args:
            key: The cache key.
            
        Returns:
            Expiration time in seconds, or None if not set or key doesn't exist.
        """
        try:
            ttl = await self.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                return None
            if ttl == -1:  # Key exists but has no expiration
                return None
            return ttl
        except Exception as e:
            logger.error(f"Error getting expiry time for key '{key}': {e}")
            return None
    
    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted.
        """
        try:
            cursor = 0
            keys_deleted = 0
            
            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.client.delete(*keys)
                    keys_deleted += len(keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Deleted {keys_deleted} keys matching pattern '{pattern}'")
            return keys_deleted
        except Exception as e:
            logger.error(f"Error clearing pattern '{pattern}': {e}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache.
        
        Args:
            key: The cache key.
            amount: Amount to increment by (default 1).
            
        Returns:
            New value after increment.
        """
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key '{key}': {e}")
            raise
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter in cache.
        
        Args:
            key: The cache key.
            amount: Amount to decrement by (default 1).
            
        Returns:
            New value after decrement.
        """
        try:
            return await self.client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Error decrementing key '{key}': {e}")
            raise
