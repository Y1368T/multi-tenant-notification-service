import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude paths that don't need auth or handle it themselves
        protected_prefixes = ("/api/admin", "/api/tenant", "/auth/logout")
        is_protected = any(request.url.path.startswith(prefix) for prefix in protected_prefixes)

        if not is_protected:
            return await call_next(request)

        token = request.cookies.get("mtns_session")
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Authentication required. Missing mtns_session cookie.", "code": "UNAUTHORIZED"}
            )

        try:
            # Stubbed: In a real scenario, the DB team's service would validate this token
            # and check if the session is still active in Redis/DB.
            # Here we just decode it without verifying the signature for stubbing purposes.
            
            # We assume it's a JWT for the stub
            payload = jwt.decode(token, options={"verify_signature": False})
            
            request.state.user_id = payload.get("user_id")
            request.state.role = payload.get("role")
            request.state.tenant_id = payload.get("tenant_id")
            
            # Basic role enforcement based on route
            if request.url.path.startswith("/api/admin") and request.state.role != "super-admin":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"message": "Super Admin access required.", "code": "FORBIDDEN"}
                )
                
            if request.url.path.startswith("/api/tenant") and request.state.role != "tenant-manager":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"message": "Tenant Manager access required.", "code": "FORBIDDEN"}
                )
                
        except Exception as e:
            logger.error(f"Failed to decode mtns_session token: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Invalid or expired session token.", "code": "UNAUTHORIZED"}
            )

        return await call_next(request)
