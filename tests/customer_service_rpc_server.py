"""Customer Management Service RPC Server.

This is a standalone RPC server that simulates the real Customer Management Service.
It consumes RPC requests from RabbitMQ, looks up customer data from JSON,
and sends responses back to the notification service.

Usage:
    python tests/customer_service_rpc_server.py
    python tests/customer_service_rpc_server.py --data-file tests/customers_data.json
"""
import asyncio
import aio_pika
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RPC Queue name (same as Notification-Microservice expects)
RPC_QUEUE = "NotificationCustomerManagementRPC"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
DEFAULT_DATA_FILE = Path(__file__).parent / "customers_data.json"


class CustomerService:
    """Customer service that handles customer data lookup."""
    
    def __init__(self, data_file: Path):
        """Initialize customer service with data file.
        
        Args:
            data_file: Path to JSON file containing customer data
        """
        self.data_file = data_file
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.load_customer_data()
    
    def load_customer_data(self):
        """Load customer data from JSON file."""
        try:
            if not self.data_file.exists():
                logger.warning(f"⚠️  Customer data file not found: {self.data_file}")
                logger.info("📝 Creating default customer data file...")
                self.create_default_data_file()
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert list to dictionary indexed by customerId
            self.customers = {}
            for customer in data.get("customers", []):
                customer_id = customer.get("customerId")
                if customer_id:
                    # Format response to match Notification-Microservice pattern
                    self.customers[customer_id] = {
                        "phone": customer.get("phone", ""),
                        "languagePreference": customer.get("languagePreference", "EN"),
                        "fullName": customer.get("fullName", ""),
                        "customerId": customer_id
                    }
            
            logger.info(f"✅ Loaded {len(self.customers)} customers from {self.data_file}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in customer data file: {e}")
            self.customers = {}
        except Exception as e:
            logger.error(f"❌ Error loading customer data: {e}", exc_info=True)
            self.customers = {}
    
    def create_default_data_file(self):
        """Create a default customer data file if it doesn't exist."""
        default_data = {
            "customers": [
                {
                    "customerId": "test_customer_123",
                    "phone": "+251911123456",
                    "languagePreference": "AM",
                    "fullName": "Test User Amharic",
                    "email": "test1@example.com",
                    "status": "active"
                },
                {
                    "customerId": "test_customer_456",
                    "phone": "+251922234567",
                    "languagePreference": "EN",
                    "fullName": "Test User English",
                    "email": "test2@example.com",
                    "status": "active"
                },
                {
                    "customerId": "test_customer_789",
                    "phone": "+251933345678",
                    "languagePreference": "OM",
                    "fullName": "Test User Oromo",
                    "email": "test3@example.com",
                    "status": "active"
                }
            ]
        }
        
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Created default customer data file: {self.data_file}")
    
    def find_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Find customer by customer ID or phone number.
        
        Args:
            customer_id: Customer ID or phone number to search for
            
        Returns:
            Customer data dictionary or None if not found
        """
        # First try direct lookup by customerId
        if customer_id in self.customers:
            return self.customers[customer_id]
        
        # If not found, try searching by phone number
        for customer in self.customers.values():
            if customer.get("phone") == customer_id:
                return customer
        
        return None
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer information.
        
        Args:
            customer_id: Customer ID or phone number
            
        Returns:
            Customer data dictionary (empty dict if not found)
        """
        customer = self.find_customer(customer_id)
        if customer:
            logger.info(f"✅ Found customer: {customer.get('fullName')} ({customer.get('languagePreference')})")
            return customer
        else:
            logger.warning(f"❌ Customer not found: {customer_id}")
            return {}


class CustomerServiceRPCServer:
    """RPC Server that handles customer management requests."""
    
    def __init__(self, customer_service: CustomerService, rabbitmq_url: str):
        """Initialize RPC server.
        
        Args:
            customer_service: CustomerService instance
            rabbitmq_url: RabbitMQ connection URL
        """
        self.customer_service = customer_service
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
    
    async def connect(self):
        """Connect to RabbitMQ."""
        try:
            logger.info(f"🔌 Connecting to RabbitMQ: {self.rabbitmq_url}")
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Set QoS to process one message at a time
            await self.channel.set_qos(prefetch_count=1)
            
            logger.info("✅ Connected to RabbitMQ")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    async def start(self):
        """Start the RPC server."""
        if not self.channel:
            await self.connect()
        
        # Declare the RPC queue
        queue = await self.channel.declare_queue(RPC_QUEUE, durable=True)
        
        logger.info(f"✅ Customer Service RPC Server listening on queue: {RPC_QUEUE}")
        logger.info(f"📋 Ready to process customer requests")
        logger.info("=" * 60)
        
        # Start consuming messages
        await queue.consume(self.process_request, no_ack=False)
        
        logger.info("🚀 Customer Service RPC Server is running. Press Ctrl+C to stop.")
    
    async def process_request(self, message: aio_pika.IncomingMessage):
        """Process an incoming RPC request.
        
        Args:
            message: Incoming RPC message
        """
        async with message.process():
            try:
                # Parse request
                request_data = json.loads(message.body.decode())
                customer_id = request_data.get("customer_id")
                
                # Get procedure from headers
                procedure = message.headers.get("procedure") if message.headers else None
                
                logger.info(f"📨 Received RPC request:")
                logger.info(f"   Procedure: {procedure}")
                logger.info(f"   Customer ID: {customer_id}")
                logger.info(f"   Correlation ID: {message.correlation_id}")
                
                # Validate procedure
                if procedure != "get_customer":
                    logger.warning(f"⚠️  Unexpected procedure: {procedure}")
                
                # Process request based on procedure
                if procedure == "get_customer":
                    response_data = await self.customer_service.get_customer(customer_id)
                else:
                    logger.warning(f"⚠️  Unknown procedure: {procedure}")
                    response_data = {}
                
                # Send response back
                if message.reply_to:
                    response = aio_pika.Message(
                        json.dumps(response_data).encode(),
                        correlation_id=message.correlation_id,
                        content_type="application/json"
                    )
                    
                    await self.channel.default_exchange.publish(
                        response,
                        routing_key=message.reply_to
                    )
                    
                    logger.info(f"📤 Sent RPC response for customer_id={customer_id}")
                else:
                    logger.error("❌ No reply_to queue specified in request")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in request: {e}")
            except Exception as e:
                logger.error(f"❌ Error processing RPC request: {e}", exc_info=True)
    
    async def stop(self):
        """Stop the RPC server."""
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        logger.info("✅ Customer Service RPC Server stopped")


async def run_server(data_file: Path, rabbitmq_url: str):
    """Run the customer service RPC server.
    
    Args:
        data_file: Path to customer data JSON file
        rabbitmq_url: RabbitMQ connection URL
    """
    customer_service = CustomerService(data_file)
    server = CustomerServiceRPCServer(customer_service, rabbitmq_url)
    
    try:
        await server.start()
        # Keep running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping Customer Service RPC Server...")
    finally:
        await server.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Customer Management Service RPC Server")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"Path to customer data JSON file (default: {DEFAULT_DATA_FILE})"
    )
    parser.add_argument(
        "--rabbitmq-url",
        type=str,
        default=RABBITMQ_URL,
        help=f"RabbitMQ connection URL (default: {RABBITMQ_URL})"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_server(args.data_file, args.rabbitmq_url))
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")


if __name__ == "__main__":
    main()