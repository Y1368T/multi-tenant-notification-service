"""Customer service client for fetching customer information via RPC.

This service communicates with the customer management microservice
to retrieve customer preferences like language settings.
"""
import logging
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

from notification_service.config.settings import Settings
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient

logger = logging.getLogger(__name__)


class CustomerServiceClient:
    """Client for interacting with customer management service via RabbitMQ RPC."""
    
  
    
    def __init__(self, rpc_client: RabbitMQRPCClient, settings: Settings):
        """Initialize customer service client.
        
        Args:
            rpc_client: RabbitMQ RPC client instance
            settings: Settings instance
        """
        self.rpc_client = rpc_client
        self.rpc_queue = settings.customer_rpc_queue
        self.rpc_timeout = settings.customer_rpc_timeout
    
    async def get_customer_language_preference(
        self,
        customer_id: str,
        timeout: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Fetch customer's preferred language from customer service.
        
        Args:
            customer_id: Customer identifier (phone number, email, or UUID)
            timeout: Request timeout in seconds (default: 5)
            
        Returns:
            Tuple of (phone, language_preference) or (None, None) if not found
            Matches the Notification-Microservice pattern
            
        Example:
            >>> client = CustomerServiceClient(rpc_client, settings)
            >>> phone, lang = await client.get_customer_language_preference("+251912345678")
            >>> print(lang)  # "am"
        """
        customer = None
        try:
            # Prepare RPC request - MATCH OLD FORMAT (Notification-Microservice pattern)
            # Only send customer_id, procedure goes in headers
            request = {
                "customer_id": customer_id
            }
            
            logger.info(f"Fetching language preference for customer: {customer_id}")
            
            # Make RPC call with procedure in headers (like old implementation)
            if self.rpc_client is None:
                raise RuntimeError("RPC client is not initialized")
            elif not self.rpc_client.is_connected:
                await self.rpc_client.connect()
            
            response = await self.rpc_client.call(
                queue_name=self.rpc_queue,
                request_data=request,
                procedure="get_customer",  # Procedure in headers (like old RPC pattern)
                timeout=timeout or self.rpc_timeout
            )
            
            # Parse response - EXPECT FULL CUSTOMER OBJECT (like old implementation)
            # Old format: {"phone": "...", "languagePreference": "EN", "fullName": "...", "customerId": "..."}
            if response:
                phone = response.get("phone")
                language_preference = response.get("languagePreference")
                
                logger.info(f"Customer {customer_id} language preference: {language_preference}, phone: {phone}")
                return phone, language_preference
            else:
                logger.warning(f"Empty response for customer {customer_id}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error fetching customer language preference: {e}")
            # Return None tuple to fall back to default language
            return None, None
    
   