# Quick Reference: RabbitMQ RPC for Customer Language Preferences

## 📋 Quick Start Checklist

- [ ] Review created files (see below)
- [ ] Update `sms_channel_handler.py` (3 changes)
- [ ] Update `main.py` (DI registration + lifespan)
- [ ] Implement RPC server in customer service
- [ ] Test with sample request
- [ ] Deploy and monitor

## 📁 Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `infrastructure/messaging/rabbitmq/rabbitmq_rpc_client.py` | RPC client implementation | ~200 |
| `infrastructure/services/customer_service_client.py` | Customer service wrapper | ~180 |
| `docs/RABBITMQ_RPC_INTEGRATION_GUIDE.md` | Complete guide | - |
| `docs/sms_handler_update_example.py` | Code examples | - |
| `docs/RPC_IMPLEMENTATION_SUMMARY.md` | This summary | - |

## 🔧 Code Changes Required

### 1. SMS Handler (`sms_channel_handler.py`)

**Line ~19** - Add import:
```python
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient
```

**Line ~31** - Add parameter:
```python
customer_service: Optional[CustomerServiceClient] = None,
```

**Line ~34** - Store reference:
```python
self.customer_service = customer_service
```

**Lines 79-80** - Replace with:
```python
language = message.lang
if not language and self.customer_service and message.recipients:
    customer_id = message.recipients[0].address
    try:
        language = await self.customer_service.get_customer_language_preference(
            customer_id=customer_id,
            tenant_id=str(tenantdb.id),
            timeout=3.0
        )
    except Exception as e:
        logger.warning(f"Failed to fetch customer language: {e}")
if not language:
    language = "en"
```

### 2. Main App (`main.py`)

**Imports**:
```python
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQRPCClient
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient
```

**DI Registration** (in `main()` function):
```python
builder.with_singleton(RabbitMQRPCClient)
builder.with_singleton(CustomerServiceClient)
```

**Lifespan** (startup):
```python
rpc_client = get_service(app, RabbitMQRPCClient)
await rpc_client.connect()
```

**Lifespan** (shutdown):
```python
await rpc_client.disconnect()
```

## 🔌 Customer Service RPC Server

### Queue Name
```
customer.rpc
```

### Request Format
```json
{
    "action": "get_customer_preference",
    "customer_id": "+251912345678",
    "preference_key": "language",
    "tenant_id": "optional-uuid"
}
```

### Response Format (Success)
```json
{
    "success": true,
    "data": {
        "language": "am"
    }
}
```

### Response Format (Error)
```json
{
    "success": false,
    "error": "Customer not found"
}
```

## 🧪 Testing Commands

### Test RPC Client
```python
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_rpc_client import RabbitMQRPCClient
from notification_service.config.settings import Settings

settings = Settings()
client = RabbitMQRPCClient(settings)
await client.connect()

response = await client.call(
    queue_name="customer.rpc",
    request_data={
        "action": "get_customer_preference",
        "customer_id": "+251912345678",
        "preference_key": "language"
    },
    timeout=5.0
)
print(response)

await client.disconnect()
```

### Test Customer Service Client
```python
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

customer_service = CustomerServiceClient(rpc_client)
language = await customer_service.get_customer_language_preference("+251912345678")
print(f"Language: {language}")
```

### Test End-to-End
Send to RabbitMQ queue `notification.sms.{tenant}`:
```json
{
    "serviceName": "payment-service",
    "recipients": [{"address": "+251912345678"}],
    "templateName": "payment_confirmation",
    "payload": {"amount": "1000"},
    "idempotencyKey": "test-123"
}
```

Expected logs:
```
INFO: Fetching language preference for customer: +251912345678
INFO: RPC request sent to 'customer.rpc' with correlation_id: abc-123
INFO: Fetched language 'am' for customer +251912345678
```

## 🎯 API Reference

### RabbitMQRPCClient

```python
class RabbitMQRPCClient:
    async def connect() -> None
    async def disconnect() -> None
    async def call(queue_name: str, request_data: Dict, timeout: float = 30.0) -> Dict
    @property is_connected -> bool
```

### CustomerServiceClient

```python
class CustomerServiceClient:
    async def get_customer_language_preference(
        customer_id: str,
        tenant_id: Optional[str] = None,
        timeout: float = 5.0
    ) -> Optional[str]
    
    async def get_customer_preferences(
        customer_id: str,
        tenant_id: Optional[str] = None,
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]
    
    async def get_customer_info(
        customer_id: str,
        tenant_id: Optional[str] = None,
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]
```

## ⚙️ Configuration

Already configured in `.env.docker`:
```env
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

Optional additions:
```env
CUSTOMER_RPC_QUEUE=customer.rpc
CUSTOMER_RPC_TIMEOUT=5.0
```

## 🛡️ Error Handling

| Error | Behavior |
|-------|----------|
| Customer service down | Falls back to "en" |
| Timeout (>3s) | Falls back to "en" |
| Customer not found | Falls back to "en" |
| Invalid response | Falls back to "en" |
| Network error | Falls back to "en" |

All errors are logged but don't break the notification flow.

## 📊 Flow Diagram

```
┌──────────────────┐                    ┌──────────────────┐
│ Notification     │                    │ Customer         │
│ Service          │                    │ Service          │
│                  │                    │                  │
│  SMS Handler     │                    │  RPC Server      │
│       ↓          │                    │       ↑          │
│  Customer Client │                    │       ↓          │
│       ↓          │                    │  Customer DB     │
│  RPC Client      │                    │                  │
│       ↓          │                    │                  │
└───────┼──────────┘                    └────────┼─────────┘
        │                                        │
        │  ① Request (correlation_id: abc-123)   │
        ├───────────────────────────────────────►│
        │     Queue: customer.rpc                │
        │                                        │
        │  ② Response (correlation_id: abc-123)  │
        │◄───────────────────────────────────────┤
        │     Queue: amq.gen-callback            │
        │     Data: {"language": "am"}           │
```

## 📝 Logging

```python
# Success flow
INFO: Fetching language preference for customer: +251912345678
INFO: RPC request sent to 'customer.rpc' with correlation_id: abc-123
INFO: RPC response received from 'customer.rpc' for correlation_id: abc-123
INFO: Fetched language 'am' for customer +251912345678

# Fallback flow
INFO: Fetching language preference for customer: +251912345678
WARNING: Failed to fetch customer language preference: Timeout
INFO: Using default language: en
```

## 🚀 Performance

- **Latency**: ~50-200ms (typical RPC call)
- **Timeout**: 3-5 seconds (configurable)
- **Async**: Non-blocking, concurrent operations
- **Connection**: Persistent, auto-reconnect

## 📚 Documentation

1. **`docs/RABBITMQ_RPC_INTEGRATION_GUIDE.md`** - Complete guide with examples
2. **`docs/sms_handler_update_example.py`** - Exact code changes
3. **`docs/RPC_IMPLEMENTATION_SUMMARY.md`** - Overview and summary
4. This file - Quick reference

## ✅ Validation

After implementation, verify:

1. RPC client connects on startup
2. Customer service RPC server is running
3. SMS without language triggers RPC call
4. Correct language is fetched and used
5. Fallback to "en" works when customer service is down
6. Logs show RPC request/response flow

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "RPC client not connected" | Ensure `await rpc_client.connect()` in lifespan |
| "Timeout" | Check customer service is running and queue exists |
| "Customer not found" | Verify customer exists in customer service DB |
| Always uses "en" | Check customer_service is injected in SMS handler |
| No RPC calls | Verify customer_service is not None in handler |

## 🎓 Key Concepts

- **RPC (Remote Procedure Call)**: Synchronous request-reply pattern
- **Correlation ID**: UUID to match requests with responses
- **Callback Queue**: Temporary queue for receiving responses
- **Timeout**: Maximum wait time for response
- **Graceful Degradation**: Falls back to default on errors

---

**Ready to integrate?** Start with updating `sms_channel_handler.py` using the examples in `docs/sms_handler_update_example.py`!
