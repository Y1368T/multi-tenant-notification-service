"""Backend session token service for signing and decoding internal JWT session tokens.

Session payload structure:
{
    "session_id": uuid,
    "user_id": uuid,
    "email": string,
    "full_name": string,
    "role": "super-admin" | "tenant-manager",
    "tenant_id": uuid | null,
    "issued_at": unix_timestamp,
    "expires_at": unix_timestamp
}
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from notification_service.config.settings import settings
from notification_service.shared.exceptions.application_exceptions import UnauthorizedError


def create_backend_session_token(
    user_id: UUID,
    email: str,
    full_name: str,
    role: str,
    tenant_id: Optional[UUID] = None,
    expires_delta_minutes: int = 60,
) -> str:
    """Create a signed backend session token with user context claims."""
    now = datetime.utcnow()
    payload = {
        "session_id": str(uuid4()),
        "user_id": str(user_id),
        "email": email,
        "full_name": full_name,
        "role": role,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "issued_at": int(now.timestamp()),
        "expires_at": int((now + timedelta(minutes=expires_delta_minutes)).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.backend_jwt_secret,
        algorithm=settings.backend_jwt_algorithm,
    )


def decode_backend_session_token(token: str) -> Dict[str, Any]:
    """Decode and verify a backend session token."""
    try:
        payload = jwt.decode(
            token,
            settings.backend_jwt_secret,
            algorithms=[settings.backend_jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Backend session token has expired")
    except jwt.PyJWTError as e:
        raise UnauthorizedError(f"Invalid backend session token: {str(e)}")
