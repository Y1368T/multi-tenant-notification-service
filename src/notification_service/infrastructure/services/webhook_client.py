"""
Webhook client service for sending callbacks to calling services.
"""
import asyncio
import logging
from typing import Dict, Optional, Any
import httpx

from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload

logger = logging.getLogger(__name__)


class WebhookClient:
    """
    HTTP client for sending webhook callbacks to calling services.
    
    Features:
    - Async HTTP POST requests
    - Retry logic with exponential backoff
    - Configurable headers for authentication
    - Timeout handling
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize WebhookClient.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def send_callback(
        self,
        callback_url: str,
        payload: NotificationCallbackPayload,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> bool:
        """
        Send webhook callback with retry logic.
        
        Args:
            callback_url: URL to POST the callback to
            payload: NotificationCallbackPayload to send
            headers: Optional HTTP headers (e.g., Authorization)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            
        Returns:
            True if callback was sent successfully, False otherwise
        """
        if not callback_url:
            logger.warning("No callback URL provided, skipping webhook")
            return False
        
        client = await self._get_client()
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "NotificationService/1.0"
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare payload
        payload_dict = payload.toDict()
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Sending callback to {callback_url} (attempt {attempt + 1}/{max_retries + 1}): "
                    f"idempotencyKey={payload.idempotencyKey}, status={payload.status}"
                )
                
                response = await client.post(
                    callback_url,
                    json=payload_dict,
                    headers=request_headers
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(
                        f"Callback sent successfully to {callback_url}: "
                        f"status_code={response.status_code}, idempotencyKey={payload.idempotencyKey}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Callback to {callback_url} returned non-success status: "
                        f"status_code={response.status_code}, body={response.text[:200]}"
                    )
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Callback to {callback_url} timed out (attempt {attempt + 1}): {e}")
            except httpx.RequestError as e:
                logger.warning(f"Callback to {callback_url} failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending callback to {callback_url}: {e}", exc_info=True)
            
            # Retry with exponential backoff
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying callback in {delay}s...")
                await asyncio.sleep(delay)
        
        logger.error(
            f"Failed to send callback to {callback_url} after {max_retries + 1} attempts: "
            f"idempotencyKey={payload.idempotencyKey}"
        )
        return False
    
    async def send_callback_dict(
        self,
        callback_url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> bool:
        """
        Send webhook callback with raw dictionary payload.
        
        Args:
            callback_url: URL to POST the callback to
            payload: Dictionary payload to send
            headers: Optional HTTP headers (e.g., Authorization)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            
        Returns:
            True if callback was sent successfully, False otherwise
        """
        if not callback_url:
            logger.warning("No callback URL provided, skipping webhook")
            return False
        
        client = await self._get_client()
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "NotificationService/1.0"
        }
        if headers:
            request_headers.update(headers)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending callback to {callback_url} (attempt {attempt + 1}/{max_retries + 1})")
                
                response = await client.post(
                    callback_url,
                    json=payload,
                    headers=request_headers
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Callback sent successfully to {callback_url}: status_code={response.status_code}")
                    return True
                else:
                    logger.warning(
                        f"Callback to {callback_url} returned non-success status: "
                        f"status_code={response.status_code}"
                    )
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Callback to {callback_url} timed out (attempt {attempt + 1}): {e}")
            except httpx.RequestError as e:
                logger.warning(f"Callback to {callback_url} failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending callback to {callback_url}: {e}", exc_info=True)
            
            # Retry with exponential backoff
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying callback in {delay}s...")
                await asyncio.sleep(delay)
        
        logger.error(f"Failed to send callback to {callback_url} after {max_retries + 1} attempts")
        return False

