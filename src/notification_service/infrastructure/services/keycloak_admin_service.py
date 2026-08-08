import httpx
import logging
from typing import Optional, Dict, Any
from notification_service.config.settings import Settings

logger = logging.getLogger(__name__)

class KeycloakAdminService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_admin_client_id
        self.client_secret = settings.keycloak_admin_client_secret

    async def _get_admin_token(self, client: httpx.AsyncClient) -> str:
        """Obtain an admin access token using client credentials."""
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = await client.post(token_url, data=data, timeout=5.0)
        response.raise_for_status()
        
        return response.json().get("access_token")

    async def create_user(self, email: str, first_name: str, last_name: str) -> str:
        """
        Creates a user in Keycloak, sets required actions for password reset,
        and returns the Keycloak user ID (sub claim).
        """
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # 1. Create User
            users_url = f"{self.base_url}/admin/realms/{self.realm}/users"
            user_payload = {
                "username": email,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "credentials": [{
                    "type": "password",
                    "value": "TemporaryPassword123!",
                    "temporary": True
                }]
            }
            
            response = await client.post(users_url, json=user_payload, headers=headers, timeout=10.0)
            
            if response.status_code == 409:
                raise ValueError("User with this email already exists in Keycloak.")
                
            response.raise_for_status()
            
            # Keycloak returns the new user's location in headers, which contains the ID.
            location = response.headers.get("Location")
            if not location:
                # If location header is missing, we must fetch the user to get the ID.
                get_response = await client.get(f"{users_url}?email={email}&exact=true", headers=headers, timeout=5.0)
                get_response.raise_for_status()
                users = get_response.json()
                if not users:
                    raise Exception("Created user could not be found.")
                user_id = users[0]["id"]
            else:
                user_id = location.rstrip('/').split('/')[-1]

            # 2. Trigger execute-actions email (UPDATE_PASSWORD)
            actions_url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/execute-actions-email"
            actions_payload = ["UPDATE_PASSWORD"]
            
            try:
                action_response = await client.put(actions_url, json=actions_payload, headers=headers, timeout=5.0)
                action_response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send UPDATE_PASSWORD action to {email}: {e}")
                # We do not fail the overall request if only the email sending fails.
                # However, in strict environments we might want to clean up. We'll proceed.
                
            return user_id

    async def delete_user(self, user_id: str) -> None:
        """Deletes a user from Keycloak by ID."""
        async with httpx.AsyncClient() as client:
            try:
                token = await self._get_admin_token(client)
                headers = {"Authorization": f"Bearer {token}"}
                
                delete_url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}"
                response = await client.delete(delete_url, headers=headers, timeout=5.0)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to delete Keycloak user {user_id}: {e}")
                raise

    async def send_password_reset_email(self, user_id: str) -> None:
        """Sends an UPDATE_PASSWORD execute-actions email to a Keycloak user."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            actions_url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/execute-actions-email"
            actions_payload = ["UPDATE_PASSWORD"]
            
            response = await client.put(actions_url, json=actions_payload, headers=headers, timeout=5.0)
            
            # 404 typically means user does not exist in Keycloak
            if response.status_code == 404:
                raise ValueError("Keycloak user not found.")
                
            response.raise_for_status()
