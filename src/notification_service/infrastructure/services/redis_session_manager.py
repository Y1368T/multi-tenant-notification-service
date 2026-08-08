import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from redis.asyncio import Redis
from redis.exceptions import RedisError, TimeoutError

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Service for managing user sessions in Redis."""

    def __init__(self, redis_client: Redis):
        """
        Initialize the RedisSessionManager.

        Args:
            redis_client: An initialized async redis-py client.
        """
        self.redis = redis_client

    def _get_key(self, session_id: str) -> str:
        """Format the Redis key for a session."""
        return f"session:{session_id}"

    async def create_session(self, user_data: dict, refresh_token: str, ttl_seconds: int = 28800) -> str:
        """
        Create a new session and store it in Redis.

        Args:
            user_data: Dictionary containing user_id, email, full_name, role, tenant_id.
            refresh_token: The Keycloak refresh token associated with the session.
            ttl_seconds: The time-to-live for the session in seconds. Defaults to 28800 (8 hours).

        Returns:
            The generated session_id as a string.
            
        Raises:
            RuntimeError: If there's an error interacting with Redis.
        """
        session_id = str(uuid.uuid4())
        key = self._get_key(session_id)
        
        now = datetime.now(timezone.utc).isoformat()
        
        payload: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_data.get("user_id"),
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "role": user_data.get("role"),
            "tenant_id": user_data.get("tenant_id"),
            "keycloak_refresh_token": refresh_token,
            "created_at": now,
            "updated_at": now,
        }
        
        try:
            await self.redis.setex(
                name=key,
                time=ttl_seconds,
                value=json.dumps(payload)
            )
            logger.debug("Session created successfully for user_id: %s with session_id: %s", payload.get("user_id"), session_id)
            return session_id
        except TimeoutError as e:
            logger.error("Redis timeout while creating session for user_id: %s: %s", payload.get("user_id"), e)
            raise RuntimeError(f"Failed to create session due to Redis timeout: {e}") from e
        except RedisError as e:
            logger.error("Redis error while creating session for user_id: %s: %s", payload.get("user_id"), e)
            raise RuntimeError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve a session from Redis by its ID.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            A dictionary containing the session data if found, None otherwise.
        """
        key = self._get_key(session_id)
        try:
            data = await self.redis.get(key)
            if not data:
                return None
            return json.loads(data)
        except TimeoutError as e:
            logger.error("Redis timeout while retrieving session_id: %s: %s", session_id, e)
            return None
        except RedisError as e:
            logger.error("Redis error while retrieving session_id: %s: %s", session_id, e)
            return None
        except json.JSONDecodeError as e:
            logger.error("Failed to decode session data for session_id: %s: %s", session_id, e)
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from Redis.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            True if the session was deleted, False if it did not exist or an error occurred.
        """
        key = self._get_key(session_id)
        try:
            result = await self.redis.delete(key)
            return bool(result > 0)
        except TimeoutError as e:
            logger.error("Redis timeout while deleting session_id: %s: %s", session_id, e)
            return False
        except RedisError as e:
            logger.error("Redis error while deleting session_id: %s: %s", session_id, e)
            return False

    async def refresh_session_ttl(self, session_id: str, ttl_seconds: int = 28800) -> bool:
        """
        Reset the expiration time for an existing session and update its timestamp.

        Args:
            session_id: The unique identifier of the session.
            ttl_seconds: The new time-to-live in seconds. Defaults to 28800 (8 hours).

        Returns:
            True if the session TTL was updated, False if the session does not exist or an error occurred.
        """
        key = self._get_key(session_id)
        try:
            data = await self.redis.get(key)
            if not data:
                return False
                
            payload = json.loads(data)
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.redis.setex(
                name=key,
                time=ttl_seconds,
                value=json.dumps(payload)
            )
            return True
        except TimeoutError as e:
            logger.error("Redis timeout while refreshing session_id: %s: %s", session_id, e)
            return False
        except RedisError as e:
            logger.error("Redis error while refreshing session_id: %s: %s", session_id, e)
            return False
        except json.JSONDecodeError as e:
            logger.error("Failed to decode session data during refresh for session_id: %s: %s", session_id, e)
            return False
