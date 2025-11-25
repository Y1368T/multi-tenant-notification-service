"""Mock RPC server for testing - simulates Customer Management Service.

This server listens on the NotificationCustomerManagementRPC queue and responds
to RPC requests matching the Notification-Microservice pattern.

Usage:
    python tests/mock_rpc_server.py
"""
import asyncio
import aio_pika
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

QUEUE_NAME = "NotificationCustomerManagementRPC"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"


# Mock customer database
MOCK_CUSTOMERS = {
    "test_customer_123": {
        "phone": "+251911123456",
        "languagePreference": "AM",
        "fullName": "Test User Amharic",
        "customerId": "test_customer_123"
    },
    "test_customer_456": {
        "phone": "+251922234567",
        "languagePreference": "EN",
        "fullName": "Test User English",
        "customerId": "test_customer_456"
    },
    "test_customer_789": {
        "phone": "+251933345678",
        "languagePreference": "OM",
        "fullName": "Test User Oromo",
        "customerId": "test_customer_789"
    },
    "invalid_customer": None  # Simulates customer not found
}


async def process_rpc_request(message: aio_pika.IncomingMessage, channel):
    """Process an incoming RPC request."""
    async with message.process():
        try:
            # Parse request
            request_data = json.loads(message.body.decode())
            customer_id = request_data.get("customer_id")
            
            # Get procedure from headers (should be "get_customer")
            procedure = message.headers.get("procedure") if message.headers else None
            
            logger.info(f"📨 Received RPC request:")
            logger.info(f"   Procedure: {procedure}")
            logger.info(f"   Customer ID: {customer_id}")
            logger.info(f"   Correlation ID: {message.correlation_id}")
            logger.info(f"   Reply To: {message.reply_to}")
            
            # Validate procedure
            if procedure != "get_customer":
                logger.warning(f"⚠️  Unexpected procedure: {procedure}")
            
            # Get customer data from mock database
            customer_data = MOCK_CUSTOMERS.get(customer_id)
            
            if customer_data is None:
                # Customer not found - return empty dict
                logger.warning(f"❌ Customer not found: {customer_id}")
                response_data = {}
            else:
                response_data = customer_data
                logger.info(f"✅ Found customer: {customer_data}")
            
            # Send response back to reply_to queue
            response = aio_pika.Message(
                json.dumps(response_data).encode(),
                correlation_id=message.correlation_id,
                content_type="application/json"
            )
            
            await channel.default_exchange.publish(
                response,
                routing_key=message.reply_to
            )
            
            logger.info(f"📤 Sent RPC response for customer_id={customer_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in request: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing RPC request: {e}", exc_info=True)


async def mock_rpc_server():
    """Run a mock RPC server that responds to customer requests."""
    connection = None
    try:
        logger.info(f"🔌 Connecting to RabbitMQ: {RABBITMQ_URL}")
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        
        # Declare the RPC queue (same as Notification-Microservice)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        logger.info(f"✅ Mock RPC server listening on queue: {QUEUE_NAME}")
        logger.info(f"📋 Mock customers available:")
        for cid, data in MOCK_CUSTOMERS.items():
            if data:
                logger.info(f"   - {cid}: {data.get('fullName')} ({data.get('languagePreference')})")
        
        # Start consuming messages
        await queue.consume(
            lambda msg: process_rpc_request(msg, channel),
            no_ack=False
        )
        
        logger.info("🚀 Mock RPC server is running. Press Ctrl+C to stop.")
        logger.info("=" * 60)
        
        # Keep running
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping mock RPC server...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
    finally:
        if connection and not connection.is_closed:
            await connection.close()
            logger.info("✅ Connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(mock_rpc_server())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")

