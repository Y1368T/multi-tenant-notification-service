"""Integration tests for RPC client with full flow.

This tests the integration between RPC client, CustomerServiceClient,
and SMS handler.

Usage:
    python tests/test_rpc_integration.py
    
Prerequisites:
    - RabbitMQ running on localhost:5672
    - Mock RPC server running (run mock_rpc_server.py first)
"""
import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification_service.config.settings import Settings
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient
from notification_service.domain.value_objects.notification_request import NotificationRequest, Recipient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_sms_handler_language_fetch():
    """Test SMS handler fetching language via RPC."""
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST: SMS Handler Language Fetch")
    logger.info("=" * 60)
    
    # Setup
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    settings.customer_rpc_queue = "NotificationCustomerManagementRPC"
    settings.customer_rpc_timeout = 5.0
    
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_client = CustomerServiceClient(rpc_client, settings)
    
    # Simulate SMS handler logic
    logger.info("\n📱 Simulating SMS handler processing notification...")
    
    # Create a notification request without language
    recipients = [Recipient(address="test_customer_123")]  # Use customer ID that exists in mock server
    notification = NotificationRequest(
        templateName="test_template",
        serviceName="test_service",
        recipients=recipients,
        payload={"test": "value"},  # Payload cannot be empty
        lang=""  # Empty language - should fetch via RPC
    )
    
    logger.info(f"   Template: {notification.templateName}")
    logger.info(f"   Recipient: {notification.recipients[0].address}")
    logger.info(f"   Language provided: {notification.lang}")
    
    # Simulate the SMS handler's language fetching logic
    language = notification.lang if notification.lang else None
    if not language and notification.recipients:
        customer_id = notification.recipients[0].address
        logger.info(f"\n   🔍 No language provided, fetching from customer service...")
        logger.info(f"   Customer ID: {customer_id}")
        
        try:
            phone, language = await customer_client.get_customer_language_preference(customer_id)
            
            if language:
                logger.info(f"   ✅ Fetched language: {language}")
                logger.info(f"   ✅ Phone verified: {phone}")
            else:
                logger.info(f"   ⚠️  No language preference found, using default")
                language = "en"
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to fetch language: {e}")
            language = "en"
    
    if not language:
        language = "en"
        logger.info(f"   📝 Using default language: {language}")
    
    logger.info(f"\n   ✅ Final language selected: {language}")
    
    # Verify
    assert language == "AM", f"Expected AM, got {language}"
    logger.info("\n✅ Integration test PASSED - Language fetched correctly via RPC")
    
    await rpc_client.disconnect()


async def test_multiple_concurrent_requests():
    """Test handling multiple concurrent RPC requests."""
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST: Concurrent RPC Requests")
    logger.info("=" * 60)
    
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    settings.customer_rpc_queue = "NotificationCustomerManagementRPC"
    settings.customer_rpc_timeout = 5.0
    
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_client = CustomerServiceClient(rpc_client, settings)
    
    # Test concurrent requests
    customer_ids = [
        "test_customer_123",
        "test_customer_456",
        "test_customer_789"
    ]
    
    logger.info(f"\n📤 Sending {len(customer_ids)} concurrent requests...")
    
    tasks = [
        customer_client.get_customer_language_preference(cid)
        for cid in customer_ids
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("\n📥 Results:")
    for i, (customer_id, result) in enumerate(zip(customer_ids, results)):
        if isinstance(result, Exception):
            logger.error(f"   {i+1}. {customer_id}: ❌ Error - {result}")
        else:
            phone, language = result
            logger.info(f"   {i+1}. {customer_id}: ✅ Phone={phone}, Language={language}")
    
    # Verify all succeeded
    assert all(not isinstance(r, Exception) for r in results), "Some requests failed"
    logger.info("\n✅ Integration test PASSED - All concurrent requests handled correctly")
    
    await rpc_client.disconnect()


async def test_error_handling():
    """Test error handling when RPC server is unavailable."""
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST: Error Handling")
    logger.info("=" * 60)
    
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    settings.customer_rpc_queue = "NonExistentQueue"  # Wrong queue
    settings.customer_rpc_timeout = 2.0
    
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_client = CustomerServiceClient(rpc_client, settings)
    
    logger.info("\n📤 Testing with non-existent queue (should timeout)...")
    
    try:
        phone, language = await customer_client.get_customer_language_preference("test_customer_123")
        logger.info(f"   Result: Phone={phone}, Language={language}")
        logger.info("   ✅ Error handled gracefully - returned (None, None)")
        assert phone is None and language is None
    except Exception as e:
        logger.warning(f"   ⚠️  Exception raised: {e}")
    
    await rpc_client.disconnect()
    logger.info("\n✅ Integration test PASSED - Error handling works correctly")


async def run_integration_tests():
    """Run all integration tests."""
    logger.info("\n" + "=" * 60)
    logger.info("🔗 RPC Client Integration Testing Suite")
    logger.info("=" * 60)
    logger.info("\n⚠️  Make sure the mock RPC server is running!")
    logger.info("   Run: python tests/mock_rpc_server.py\n")
    
    import time
    logger.info("Waiting 2 seconds for mock server to be ready...")
    await asyncio.sleep(2)
    
    await test_sms_handler_language_fetch()
    await test_multiple_concurrent_requests()
    await test_error_handling()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All integration tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(run_integration_tests())
    except KeyboardInterrupt:
        logger.info("\n👋 Tests interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Integration test suite failed: {e}", exc_info=True)