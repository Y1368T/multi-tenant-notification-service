from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IKeycloakClient(ABC):
    """Interface for all Keycloak operations."""

    @abstractmethod
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user against Keycloak.
        
        Calls the Keycloak token endpoint using Resource Owner Password Grant.
        
        Returns dict with:
            - access_token: str
            - refresh_token: str
            - expires_in: int
            - token_type: str
        
        Raises:
            UnauthorizedError: if credentials are invalid
        """
        pass

    @abstractmethod
    async def register(
        self,
        email: str,
        password: str,
        firstName: str,
        lastName: str
    ) -> str:
        """Create a new user in Keycloak via Admin REST API.
        
        Returns:
            keycloakId (str): The new user's Keycloak ID (UUID string)
        
        Raises:
            ConflictError: if email already exists in Keycloak
        """
        pass

    @abstractmethod
    async def logout(self, refreshToken: str) -> None:
        """Revoke the user's refresh token in Keycloak.
        
        After this call, both the refresh token and any access tokens
        derived from it become invalid.
        """
        pass

    @abstractmethod
    async def refreshToken(self, refreshToken: str) -> Dict[str, Any]:
        """Exchange a refresh token for a new access + refresh token pair.
        
        Returns dict with:
            - access_token: str
            - refresh_token: str
            - expires_in: int
        
        Raises:
            UnauthorizedError: if refresh token is expired or invalid
        """
        pass

    @abstractmethod
    async def verifyToken(self, accessToken: str) -> Dict[str, Any]:
        """Verify a JWT access token using Keycloak's public JWKS.
        
        Verification is done locally (no network call per request).
        JWKS keys are fetched once and cached.
        
        Returns:
            payload (dict): Decoded JWT claims including 'sub' (keycloakId),
                            'email', 'realm_access', 'exp', etc.
        
        Raises:
            UnauthorizedError: if token is invalid, expired, or tampered
        """
        pass

    @abstractmethod
    async def getUserRoles(self, keycloakId: str) -> list[str]:
        """Get all realm roles for a Keycloak user.
        
        Returns:
            List of role name strings (e.g., ['admin', 'default-roles-realm'])
        """
        pass
