# RabbitMQ RPC Implementation Guide for Customer Service Integration

## Overview

This guide explains how to integrate RabbitMQ RPC (Request-Reply Pattern) to fetch customer language preferences from the Customer Service microservice in your Notification Service.

## Architecture

```
┌─────────────────────────┐         RabbitMQ RPC          ┌──────────────────────┐
│  Notification Service   │◄──────────────────────────────►│  Customer Service    │
│                         │                                │                      │
│  - SMS Handler          │   Request: Get Language        │  - Customer Data     │
│  - RPC Client           │   Response: "en", "am", "or"   │  - RPC Server        │
└─────────────────────────┘                                └──────────────────────┘
```

## Files Created

### 1. RabbitMQ RPC Client (`infrastructure/messaging/rabbitmq/rabbitmq_rpc_client.py`)

**Purpose**: Low-level RPC client for making synchronous request-reply calls via RabbitMQ

**Key Features**:
- Creates temporary callback queue for receiving responses
- Uses correlation IDs to match requests with responses
- Supports timeout configuration
- Handles connection management and error handling

**Usage**:
```python
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient

# Initialize
rpc_client = RabbitMQRPCClient(settings)
await rpc_client.connect()

# Make RPC call
response = await rpc_client.call(
    queue_name="customer.rpc",
    request_data={"action": "get_customer", "customer_id": "123"},
    timeout=5.0
)

# Cleanup
await rpc_client.disconnect()
```

### 2. Customer Service Client (`infrastructure/services/customer_service_client.py`)

**Purpose**: High-level client for interacting with Customer Service via RPC

**Key Methods**:

#### `get_customer_language_preference(customer_id, tenant_id=None, timeout=5.0)`
Fetches customer's preferred language.

**Parameters**:
- `customer_id`: Customer identifier (phone number, email, or UUID)
- `tenant_id`: Optional tenant ID for multi-tenant isolation
- `timeout`: Request timeout in seconds (default: 5)

**Returns**: Language code (e.g., "en", "am", "or") or None if not found

**Example**:
```python
customer_service = CustomerServiceClient(rpc_client)
language = await customer_service.get_customer_language_preference("+251912345678")
# Returns: "am" or None
```

#### `get_customer_preferences(customer_id, tenant_id=None, timeout=5.0)`
Fetches all customer preferences.

**Returns**:
```json
{
    "language": "am",
    "timezone": "Africa/Addis_Ababa",
    "notification_channels": ["sms", "email"],
    "opt_out": false
}
```

#### `get_customer_info(customer_id, tenant_id=None, timeout=5.0)`
Fetches complete customer information.

**Returns**:
```json
{
    "id": "uuid",
    "name": "John Doe",
    "phone": "+251912345678",
    "email": "john@example.com",
    "language": "en",
    "created_at": "2024-01-01T00:00:00Z"
}
```

## Integration Steps

### Step 1: Update SMS Channel Handler

Add the customer service client to `sms_channel_handler.py`:

```python
# Add import at the top
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

# Update constructor
class SMSChannelHandler(IChannelHandler):
    def __init__(
        self,
        unitofWork: IUnitOfWork,
        afro_service: AfromessageSMSProvider,
        kifiya_service: KifiyaSMSProvider,
        jasmin_service: JasminSMSProvider,
        redis: RedisCache,
        customer_service: Optional[CustomerServiceClient] = None,  # ADD THIS
    ):
        self.unitofWork = unitofWork
        self.redis = redis
        self.customer_service = customer_service  # ADD THIS
        self.__handlers = {
            SMSProvider.AFROMESSAGE: afro_service,
            SMSProvider.KIFIYA: kifiya_service,
            SMSProvider.JASMIN: jasmin_service,
        }
```

### Step 2: Update `receiveMessage` Method

Replace line 79-80 in `sms_channel_handler.py`:

**BEFORE**:
```python
# send grpc request to customer management service to get customer language preference for Qena system
language = message.lang if message.lang else "en"
```

**AFTER**:
```python
# Fetch customer language preference from customer service via RPC
language = message.lang  # Start with provided language
        
if not language and self.customer_service:
    # If no language provided, try to fetch from customer service
    # Use recipient's address as customer identifier
    if getattr(message, "recipient", None):
        customer_id = message.recipient.address
        try:
            language = await self.customer_service.get_customer_language_preference(
                customer_id=customer_id,
                tenant_id=str(tenantdb.id),
                timeout=3.0  # 3 second timeout
            )
            if language:
                logger.info(f"Fetched language '{language}' for customer {customer_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch customer language, using default: {e}")
            
# Fall back to default language if still not set
if not language:
    language = "en"
```

### Step 3: Register Services in Dependency Injection

Update `main.py` to register the RPC client and customer service:

```python
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQRPCClient
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

def main() -> FastAPI:
    builder = (Builder()
        .with_title("Notification Service")
        .with_description("Service for sending notifications via email and SMS")
        .with_version("1.0.0")
        .with_lifespan(lifespan))
    
    # ... existing registrations ...
    
    # Register RPC client as singleton
    builder.with_singleton(RabbitMQRPCClient)
    
    # Register customer service client as singleton
    builder.with_singleton(CustomerServiceClient)
    
    # Update SMS handler registration to include customer service
    builder.with_transient(SMSChannelHandler)
    
    # ... rest of the code ...
```

### Step 4: Initialize RPC Client in Lifespan

Update the `lifespan` function in `main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    db = get_service(app, Database)
    await db.connect()
    
    redis = get_service(app, RedisCache)
    await redis.connect()
    
    # Initialize RPC client for customer service
    rpc_client = get_service(app, RabbitMQRPCClient)
    await rpc_client.connect()
    logger.info("RabbitMQ RPC client connected")
    
    # ... existing code ...
    
    try:
        yield
    finally:
        # Shutdown actions
        await adapterConsumer.stopConsuming()
        await rpc_client.disconnect()  # ADD THIS
        db.disconnect()
        redis.disconnect()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
```

## Customer Service RPC Server Implementation

The customer service needs to implement an RPC server that listens on the `customer.rpc` queue.

### Expected Request Format

```json
{
    "action": "get_customer_preference",
    "customer_id": "+251912345678",
    "preference_key": "language",
    "tenant_id": "optional-tenant-uuid"
}
```

### Expected Response Format

**Success**:
```json
{
    "success": true,
    "data": {
        "language": "am"
    }
}
```

**Error**:
```json
{
    "success": false,
    "error": "Customer not found"
}
```

### Sample RPC Server (Customer Service)

```python
import json
import aio_pika
from aio_pika import Message, DeliveryMode

async def handle_rpc_request(message: aio_pika.IncomingMessage):
    """Handle RPC requests from notification service."""
    async with message.process():
        try:
            # Parse request
            request = json.loads(message.body.decode())
            action = request.get("action")
            customer_id = request.get("customer_id")
            
            # Process request
            if action == "get_customer_preference":
                # Fetch from database
                customer = await get_customer_from_db(customer_id)
                preference_key = request.get("preference_key")
                
                response = {
                    "success": True,
                    "data": {
                        preference_key: customer.get(preference_key)
                    }
                }
            else:
                response = {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
            
            # Send response
            response_message = Message(
                body=json.dumps(response).encode(),
                correlation_id=message.correlation_id,
                delivery_mode=DeliveryMode.PERSISTENT
            )
            
            await channel.default_exchange.publish(
                response_message,
                routing_key=message.reply_to
            )
            
        except Exception as e:
            # Send error response
            error_response = {
                "success": False,
                "error": str(e)
            }
            
            response_message = Message(
                body=json.dumps(error_response).encode(),
                correlation_id=message.correlation_id
            )
            
            await channel.default_exchange.publish(
                response_message,
                routing_key=message.reply_to
            )

# Setup RPC server
connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
channel = await connection.channel()

# Declare RPC queue
rpc_queue = await channel.declare_queue("customer.rpc", durable=True)

# Start consuming
await rpc_queue.consume(handle_rpc_request)
```

## Testing

### 1. Test RPC Client Directly

```python
import asyncio
from notification_service.config.settings import Settings
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient

async def test_rpc():
    settings = Settings()
    client = RabbitMQRPCClient(settings)
    
    await client.connect()
    
    try:
        response = await client.call(
            queue_name="customer.rpc",
            request_data={
                "action": "get_customer_preference",
                "customer_id": "+251912345678",
                "preference_key": "language"
            },
            timeout=5.0
        )
        print(f"Response: {response}")
    finally:
        await client.disconnect()

# Run test
asyncio.run(test_rpc())
```

### 2. Test Customer Service Client

```python
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

async def test_customer_service():
    rpc_client = RabbitMQRPCClient(settings)
    await rpc_client.connect()
    
    customer_service = CustomerServiceClient(rpc_client)
    
    # Test language preference
    language = await customer_service.get_customer_language_preference("+251912345678")
    print(f"Language: {language}")
    
    # Test all preferences
    prefs = await customer_service.get_customer_preferences("+251912345678")
    print(f"Preferences: {prefs}")
    
    await rpc_client.disconnect()

asyncio.run(test_customer_service())
```

### 3. Test End-to-End

Send a notification request without language specified:

```json
{
    "serviceName": "payment-service",
    "recipient": {"address": "+251912345678"},
    "templateName": "payment_confirmation",
    "payload": {"amount": "1000", "currency": "ETB"},
    "idempotencyKey": "test-123"
    // Note: no "lang" field - should fetch from customer service
}
```

## Error Handling

The implementation includes robust error handling:

1. **Timeout**: If RPC call takes too long, falls back to default language
2. **Service Unavailable**: If customer service is down, uses default language
3. **Customer Not Found**: Returns None, falls back to default language
4. **Network Errors**: Catches exceptions and logs warnings

## Performance Considerations

1. **Timeout**: Default 5 seconds, configurable per call
2. **Caching**: Consider caching customer preferences in Redis
3. **Fallback**: Always has a default language fallback
4. **Async**: Non-blocking RPC calls using asyncio

## Configuration

Add to `.env` if needed:

```env
# RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Customer Service RPC Configuration
CUSTOMER_RPC_QUEUE=customer.rpc
CUSTOMER_RPC_TIMEOUT=5.0
```

## Monitoring & Logging

The implementation includes comprehensive logging:

```
INFO: Fetching language preference for customer: +251912345678
INFO: RPC request sent to 'customer.rpc' with correlation_id: abc-123
INFO: RPC response received from 'customer.rpc' for correlation_id: abc-123
INFO: Customer +251912345678 language preference: am
```

## Summary

You now have:
1. ✅ **RabbitMQ RPC Client** - Low-level RPC communication
2. ✅ **Customer Service Client** - High-level customer service integration
3. ✅ **Integration Guide** - Step-by-step implementation instructions
4. ✅ **Testing Examples** - How to test the implementation
5. ✅ **Error Handling** - Robust fallback mechanisms

Next steps:
1. Update `sms_channel_handler.py` with the code from Step 2
2. Update `main.py` with DI registration from Step 3 & 4
3. Ensure customer service implements the RPC server
4. Test the integration end-to-end
