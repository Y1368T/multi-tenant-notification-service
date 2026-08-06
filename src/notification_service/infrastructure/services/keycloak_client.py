"""Keycloak client — infrastructure adapter for IKeycloakClient port.

Responsibilities:
    1. login()        → Keycloak Token Endpoint (password grant)
    2. register()     → Keycloak Admin REST API (create user)
    3. logout()       → Keycloak Token Endpoint (revoke)
    4. refreshToken() → Keycloak Token Endpoint (refresh grant)
    5. verifyToken()  → Local JWKS verification (no network per request)
    6. getUserRoles() → Keycloak Admin REST API
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from jose import JWTError, jwt

from notification_service.config.settings import Settings
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.shared.exceptions.application_exceptions import (
    ConflictError,
    UnauthorizedError,
    ApplicationException,
)

logger = logging.getLogger(__name__)


class KeycloakClient(IKeycloakClient):
    """Concrete implementation of IKeycloakClient using httpx + python-jose."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._base_url = settings.keycloak_url.rstrip("/")
        self._realm = settings.keycloak_realm
        self._client_id = settings.keycloak_client_id
        self._client_secret = settings.keycloak_client_secret
        self._admin_username = settings.keycloak_admin_username
        self._admin_password = settings.keycloak_admin_password

        # Token endpoint
        self._token_url = (
            f"{self._base_url}/realms/{self._realm}"
            f"/protocol/openid-connect/token"
        )
        # Logout endpoint
        self._logout_url = (
            f"{self._base_url}/realms/{self._realm}"
            f"/protocol/openid-connect/logout"
        )
        # JWKS endpoint (for local token verification)
        self._jwks_url = (
            f"{self._base_url}/realms/{self._realm}"
            f"/protocol/openid-connect/certs"
        )
        # Admin REST API base
        self._admin_url = (
            f"{self._base_url}/admin/realms/{self._realm}"
        )

        # In-memory JWKS cache (keys don't change often)
        self._jwks_cache: Optional[Dict] = None

    # LOGIN
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Resource Owner Password Grant."""
        payload = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": email,
            "password": password,
            "scope": "openid profile email",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload)

        if response.status_code == 401:
            raise UnauthorizedError("Invalid email or password")
        if response.status_code != 200:
            logger.error(f"Keycloak login failed: {response.text}")
            raise ApplicationException("Authentication service error", code="KEYCLOAK_ERROR")

        data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "token_type": data.get("token_type", "Bearer"),
        }

    # REGISTER (Keycloak Admin API)
    async def register(
        self,
        email: str,
        password: str,
        firstName: str,
        lastName: str,
    ) -> str:
        """Create user in Keycloak. Returns the new user's keycloakId."""
        # Step A: get an admin access token (client credentials)
        admin_token = await self._getAdminToken()

        # Step B: create the user
        user_payload = {
            "username": email,
            "email": email,
            "firstName": firstName,
            "lastName": lastName,
            "enabled": True,
            "emailVerified": True,
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": False,
                }
            ],
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._admin_url}/users",
                json=user_payload,
                headers=headers,
            )

        if response.status_code == 409:
            raise ConflictError(
                f"A user with email '{email}' already exists in Keycloak"
            )
        if response.status_code not in (201, 200):
            logger.error(f"Keycloak register failed: {response.text}")
            raise ApplicationException("Failed to create user in Keycloak", code="KEYCLOAK_ERROR")

        # Step C: extract the new user's ID from the Location header
        # Location: .../admin/realms/{realm}/users/{keycloak_user_id}
        location = response.headers.get("Location", "")
        keycloak_id = location.split("/")[-1]
        if not keycloak_id:
            raise ApplicationException("Failed to extract Keycloak user ID", code="KEYCLOAK_ERROR")

        return keycloak_id

    # LOGOUT

    async def logout(self, refreshToken: str) -> None:
        """Revoke the refresh token in Keycloak."""
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refreshToken,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._logout_url, data=payload)

        if response.status_code not in (200, 204):
            logger.warning(f"Keycloak logout returned {response.status_code}: {response.text}")
            # Don't raise — logout should be best-effort

    # REFRESH TOKEN

    async def refreshToken(self, refreshToken: str) -> Dict[str, Any]:
        """Exchange a refresh token for new tokens."""
        payload = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refreshToken,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload)

        if response.status_code in (400, 401):
            raise UnauthorizedError("Refresh token is expired or invalid")
        if response.status_code != 200:
            raise ApplicationException("Token refresh failed", code="KEYCLOAK_ERROR")

        data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "token_type": data.get("token_type", "Bearer"),
        }

    # 
    # VERIFY TOKEN (local — no network call per request)
    # 
    async def verifyToken(self, accessToken: str) -> Dict[str, Any]:
        """Verify JWT locally using Keycloak's JWKS public keys."""
        jwks = await self._getJwks()
        try:
            # python-jose will select the correct key by 'kid' header
            payload = jwt.decode(
                accessToken,
                jwks,
                algorithms=["RS256"],
                audience=self._client_id,
                options={"verify_aud": False},  # set True in strict production
            )
            return payload
        except JWTError as e:
            raise UnauthorizedError(f"Invalid or expired token: {str(e)}")

    # GET USER ROLES
    
    async def getUserRoles(self, keycloakId: str) -> List[str]:
        """Get realm roles for a Keycloak user."""
        admin_token = await self._getAdminToken()
        headers = {"Authorization": f"Bearer {admin_token}"}
        url = f"{self._admin_url}/users/{keycloakId}/role-mappings/realm"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            logger.warning(f"Could not fetch roles for user {keycloakId}: {response.text}")
            return []

        roles = response.json()
        return [r["name"] for r in roles]

    # PRIVATE HELPERS

    async def _getAdminToken(self) -> str:
        """Get a short-lived admin access token using client credentials."""
        payload = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._admin_username,
            "password": self._admin_password,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload)

        if response.status_code != 200:
            raise ApplicationException(
                "Failed to get Keycloak admin token", code="KEYCLOAK_ADMIN_ERROR"
            )
        return response.json()["access_token"]

    async def _getJwks(self) -> Dict:
        """Fetch JWKS from Keycloak (cached in memory).
        
        In production, you can add a TTL or use your existing Redis cache.
        """
        if self._jwks_cache is not None:
            return self._jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(self._jwks_url)

        if response.status_code != 200:
            raise ApplicationException("Failed to fetch JWKS from Keycloak", code="KEYCLOAK_JWKS_ERROR")

        self._jwks_cache = response.json()
        logger.info("JWKS keys fetched and cached from Keycloak")
        return self._jwks_cache
