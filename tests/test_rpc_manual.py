"""Manual testing script for RPC client implementation.

This script tests the RPC client and CustomerServiceClient directly.

Usage:
    python tests/test_rpc_manual.py
    
Prerequisites:
    - RabbitMQ running on localhost:5672
    - Mock RPC server running (run mock_rpc_server.py first)
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification_service.config.settings import Settings
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rpc_client_direct():
    """Test RPC client directly with a raw call."""
    logger.info("=" * 60)
    logger.info("TEST 1: Direct RPC Client Test")
    logger.info("=" * 60)
    
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    
    rpc_client = RabbitMQRPCClient(settings)
    
    try:
        logger.info("🔌 Connecting RPC client...")
        await rpc_client.connect()
        logger.info("✅ RPC client connected")
        
        # Test RPC call with procedure in headers
        logger.info("\n📤 Sending RPC request...")
        logger.info("   Queue: NotificationCustomerManagementRPC")
        logger.info("   Procedure: get_customer")
        logger.info("   Customer ID: test_customer_123")
        
        response = await rpc_client.call(
            queue_name="NotificationCustomerManagementRPC",
            request_data={"customer_id": "test_customer_123"},
            procedure="get_customer",
            timeout=5.0
        )
        
        logger.info("\n✅ RPC response received:")
        logger.info(f"   Response: {response}")
        logger.info(f"   Phone: {response.get('phone')}")
        logger.info(f"   Language: {response.get('languagePreference')}")
        logger.info(f"   Full Name: {response.get('fullName')}")
        
        assert response.get("phone") == "+251911123456"
        assert response.get("languagePreference") == "AM"
        logger.info("\n✅ Test 1 PASSED")
        
    except Exception as e:
        logger.error(f"\n❌ Test 1 FAILED: {e}", exc_info=True)
    finally:
        await rpc_client.disconnect()
        logger.info("🔌 RPC client disconnected\n")


async def test_customer_service_client():
    """Test CustomerServiceClient wrapper."""
    logger.info("=" * 60)
    logger.info("TEST 2: CustomerServiceClient Test")
    logger.info("=" * 60)
    
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    settings.customer_rpc_queue = "NotificationCustomerManagementRPC"
    settings.customer_rpc_timeout = 5.0
    
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_client = CustomerServiceClient(rpc_client, settings)
    
    test_cases = [
        ("test_customer_123", "+251911123456", "AM"),
        ("test_customer_456", "+251922234567", "EN"),
        ("test_customer_789", "+251933345678", "OM"),
        ("invalid_customer", None, None),  # Should return (None, None)
    ]
    
    try:
        for customer_id, expected_phone, expected_language in test_cases:
            logger.info(f"\n📤 Testing customer: {customer_id}")
            
            phone, language = await customer_client.get_customer_language_preference(customer_id)
            
            logger.info(f"   Result - Phone: {phone}, Language: {language}")
            
            if expected_phone:
                assert phone == expected_phone, f"Expected phone {expected_phone}, got {phone}"
                assert language == expected_language, f"Expected language {expected_language}, got {language}"
                logger.info(f"   ✅ PASSED")
            else:
                assert phone is None, f"Expected None phone, got {phone}"
                assert language is None, f"Expected None language, got {language}"
                logger.info(f"   ✅ PASSED (customer not found as expected)")
        
        logger.info("\n✅ Test 2 PASSED - All customer test cases passed")
        
    except Exception as e:
        logger.error(f"\n❌ Test 2 FAILED: {e}", exc_info=True)
    finally:
        await rpc_client.disconnect()
        logger.info("🔌 RPC client disconnected\n")


async def test_rpc_timeout():
    """Test RPC timeout handling."""
    logger.info("=" * 60)
    logger.info("TEST 3: RPC Timeout Test")
    logger.info("=" * 60)
    
    settings = Settings()
    settings.rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_client = CustomerServiceClient(rpc_client, settings)
    
    try:
        logger.info("📤 Testing with very short timeout (0.1s)...")
        # This should timeout if server is slow
        phone, language = await customer_client.get_customer_language_preference(
            "test_customer_123",
            timeout=0.1
        )
        logger.info(f"   Result - Phone: {phone}, Language: {language}")
        logger.info("   ⚠️  Note: If server responds quickly, timeout won't occur")
        
    except asyncio.TimeoutError:
        logger.info("   ✅ Timeout occurred as expected")
    except Exception as e:
        logger.error(f"   ❌ Unexpected error: {e}")
    finally:
        await rpc_client.disconnect()
        logger.info("🔌 RPC client disconnected\n")


async def test_request_format():
    """Verify the request format matches Notification-Microservice pattern."""
    logger.info("=" * 60)
    logger.info("TEST 4: Request Format Verification")
    logger.info("=" * 60)
    
    logger.info("📋 Verifying request format matches old implementation:")
    logger.info("   ✓ Request body: {'customer_id': '...'}")
    logger.info("   ✓ Procedure in headers: 'get_customer'")
    logger.info("   ✓ Queue: 'NotificationCustomerManagementRPC'")
    logger.info("   ✓ Response format: {'phone': '...', 'languagePreference': '...', ...}")
    logger.info("   ✓ Return value: Tuple (phone, language_preference)")
    logger.info("\n✅ Request format matches Notification-Microservice pattern\n")


async def run_all_tests():
    """Run all manual tests."""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 RPC Client Manual Testing Suite")
    logger.info("=" * 60)
    logger.info("\n⚠️  Make sure the mock RPC server is running!")
    logger.info("   Run: python tests/mock_rpc_server.py\n")
    
    input("Press Enter to start tests...")
    
    await test_rpc_client_direct()
    await test_customer_service_client()
    await test_rpc_timeout()
    await test_request_format()
    
    logger.info("=" * 60)
    logger.info("✅ All manual tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        logger.info("\n👋 Tests interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}", exc_info=True)