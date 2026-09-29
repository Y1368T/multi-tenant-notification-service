import jwt
import logging
from typing import Set
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from notification_service.config.settings import Settings
from notification_service.infrastructure.services.redis_session_manager import RedisSessionManager
from qena_shared_lib.dependencies.http import get_service

logger = logging.getLogger(__name__)

# List of endpoints that do not require authentication
EXEMPT_PATHS: Set[str] = {
    "/auth/login",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json"
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Check if path is exempt
        path = request.url.path
        if path.startswith("/auth") or path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # 2. Extract mtns_session token from cookies or Authorization header
        token = request.cookies.get("mtns_session")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()

        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Authentication required. Missing mtns_session cookie or Bearer token.", "code": "UNAUTHORIZED"}
            )

        # Retrieve dependencies
        redis_session_manager = None
        try:
            settings = get_service(request.app, Settings)
        except Exception as e:
            logger.error("Failed to retrieve Settings in AuthMiddleware: %s", e)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Internal server configuration error.", "code": "INTERNAL_ERROR"}
            )

        try:
            redis_session_manager = get_service(request.app, RedisSessionManager)
        except Exception as e:
            logger.debug("RedisSessionManager not available: %s", e)

        try:
            # 3. Verify token signature (try session_signing_key, then backend_jwt_secret)
            payload = None
            for key, alg in [
                (settings.session_signing_key, "HS256"),
                (settings.backend_jwt_secret, getattr(settings, "backend_jwt_algorithm", "HS256")),
            ]:
                try:
                    payload = jwt.decode(token, key, algorithms=[alg])
                    break
                except Exception:
                    continue

            if not payload:
                raise jwt.InvalidTokenError("Could not decode token with configured keys")

            session_id = payload.get("session_id")
                
            # 4. Fetch session data from Redis via RedisSessionManager if available
            session_data = None
            if session_id and redis_session_manager:
                try:
                    session_data = await redis_session_manager.get_session(session_id)
                except Exception as e:
                    logger.debug("Redis session lookup failed: %s", e)

            # If not in Redis, fallback to payload claims if role is present
            if not session_data and payload.get("role"):
                session_data = payload

            if not session_data:
                # Session is expired or invalid
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"message": "Session expired or invalid.", "code": "UNAUTHORIZED"}
                )
            
            # 5. Attach user context to request.state
            request.state.user = session_data
            
            # Also attach these individually for backward compatibility if needed
            request.state.user_id = session_data.get("user_id")
            request.state.role = session_data.get("role")
            request.state.tenant_id = session_data.get("tenant_id")
            request.state.session_id = session_id
            
            # Basic role enforcement based on route
            if path.startswith("/api/admin") and request.state.role != "super-admin":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"message": "This account does not have access to the admin portal.", "code": "FORBIDDEN"}
                )
                
            if path.startswith("/api/tenant") and request.state.role != "tenant-manager":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"message": "This account does not have access to the tenant portal.", "code": "FORBIDDEN"}
                )
                
        except jwt.ExpiredSignatureError:
            logger.warning("Expired session token provided.")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Session token has expired.", "code": "UNAUTHORIZED"}
            )
        except jwt.PyJWTError as e:
            logger.warning("Invalid session token provided: %s", e)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Invalid session token.", "code": "UNAUTHORIZED"}
            )
        except Exception as e:
            logger.error("Failed to decode mtns_session token: %s", e)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Invalid or expired session token.", "code": "UNAUTHORIZED"}
            )

        return await call_next(request)
