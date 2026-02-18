# Notification Service - Developer Integration Guide

> **Version:** 1.1.0  
> **Last Updated:** February 18, 2026

A comprehensive guide for developers integrating their applications with the Notification Service. This service provides multi-channel notification capabilities including **SMS**, **Email**, and **In-App (Push)** notifications.

---
****
## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
4. [Authentication](#authentication)
5. [Integration Methods](#integration-methods)
   - [REST API](#rest-api-integration)
   - [RabbitMQ](#rabbitmq-integration)
6. [Notification Channels](#notification-channels)
   - [SMS Notifications](#sms-notifications)
   - [Email Notifications](#email-notifications)
   - [In-App Notifications](#in-app-notifications)
7. [Templates](#templates)
8. [Tenant Configuration](#tenant-configuration)
9. [Provider Configuration](#provider-configuration)
10. [Processing Modes](#processing-modes)
    - [Fire-and-Forget Mode](#1-fire-and-forget-mode-default)
    - [Immediate Mode (RPC)](#2-immediate-mode-rpc)
11. [Callbacks & Webhooks](#callbacks--webhooks)
    - [Callback Configuration Levels](#callback-configuration-levels)
    - [When Callbacks Are Sent](#when-callbacks-are-sent)
    - [Callback Payload](#callback-payload)
    - [Per-Request Callbacks](#per-request-callbacks)
    - [Tenant-Level Callbacks](#tenant-level-callbacks)
12. [Outbox Pattern & Retry Mechanism](#outbox-pattern--retry-mechanism)
13. [API Reference](#api-reference)
14. [Error Handling](#error-handling)
15. [Best Practices](#best-practices)
16. [Troubleshooting](#troubleshooting)

---

## Overview

The Notification Service is a multi-tenant, multi-channel notification platform that enables applications to send notifications through various channels:

| Channel | Description | Providers |
|---------|-------------|-----------|
| **SMS** | Text messages to mobile phones | Afromessage, Kifiya, Jasmin |
| **Email** | Email messages with HTML/text support | SMTP, SendGrid, Mailgun, Amazon SES |
| **In-App** | Push notifications to mobile/web apps | Firebase Cloud Messaging (FCM) |

### Key Features

- ✅ **Multi-tenant** - Isolated configurations per tenant
- ✅ **Multi-channel** - SMS, Email, and Push notifications
- ✅ **Template-based** - Reusable templates with variable substitution
- ✅ **Multi-language** - Templates support multiple languages
- ✅ **Rate limiting** - Configurable rate limits per provider
- ✅ **Retry mechanism** - Automatic retry with exponential backoff
- ✅ **Idempotency** - Duplicate detection via idempotency keys
- ✅ **Callbacks** - Webhook notifications for delivery status

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Your Application                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    │ REST API                           │ RabbitMQ
                    ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NOTIFICATION SERVICE                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │   REST API   │  │   RabbitMQ   │  │   Templates  │                       │
│  │   Endpoints  │  │   Consumer   │  │   Engine     │                       │
│  └──────────────┘  └──────────────┘  └──────────────┘                       │
│         │                 │                 │                                │
│         └─────────────────┼─────────────────┘                                │
│                           ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Message Router                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │ SMS Handler │     │Email Handler│     │InApp Handler│                    │
│  └─────────────┘     └─────────────┘     └─────────────┘                    │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │ SMS Providers│    │Email Provider│    │ FCM Provider│                    │
│  │ • Afromessage│    │ • SMTP      │     │             │                    │
│  │ • Kifiya     │    │ • SendGrid  │     │             │                    │
│  │ • Jasmin     │    │ • Mailgun   │     │             │                    │
│  └─────────────┘     └─────────────┘     └─────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Step 1: Register Your Tenant

Contact the system administrator to create a tenant for your application. You'll receive:

- **Tenant ID** (UUID)
- **API Key** for authentication
- **Tenant Prefix** (e.g., `MYAPP`) for RabbitMQ queue naming

### Step 2: Configure Providers

Set up at least one provider for each channel you want to use:

- SMS: Configure Afromessage, Kifiya, or Jasmin credentials
- Email: Configure SMTP or cloud email service credentials  
- In-App: Configure Firebase Cloud Messaging (FCM) credentials

### Step 3: Create Templates

Create notification templates for each type of notification you'll send.

### Step 4: Send Notifications

Choose your integration method (REST API or RabbitMQ) and start sending notifications!

---

## Authentication

All API requests require authentication via API key.

### Header Authentication

```http
X-API-Key: your-tenant-api-key-here
```

### Example Request

```bash
curl -X POST "https://notification-service.example.com/sms-notifications/send" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{...}'
```

### Regenerating API Keys

If your API key is compromised, request a new one:

```http
POST /tenants/{tenant_id}/regenerate-api-key
```

---

## Integration Methods

### REST API Integration

Direct HTTP calls to the notification service endpoints.

**Base URL:** `https://notification-service.example.com`

#### Sending an SMS via REST

```bash
curl -X POST "https://notification-service.example.com/sms-notifications/send?tenant_id=YOUR_TENANT_UUID" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "serviceName": "payment-service",
    "recipients": [
      {"address": "+251912345678"}
    ],
    "templateName": "payment_confirmation",
    "payload": {
      "amount": "1000.00",
      "currency": "ETB",
      "transactionId": "TXN123456"
    },
    "idempotencyKey": "unique-request-id-12345",
    "lang": "en",
    "callbackUrl": "https://your-service.internal/webhooks/sms",
    "callbackHeaders": {
      "Authorization": "Bearer your-webhook-secret"
    }
  }'
```

> **Note:** The `callbackUrl` and `callbackHeaders` are optional. If provided, you'll receive an HTTP POST when the notification is successfully delivered or permanently fails.

#### Sending an Email via REST

```bash
curl -X POST "https://notification-service.example.com/email-notifications/send?tenant_id=YOUR_TENANT_UUID" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "serviceName": "user-service",
    "recipients": [
      {"address": "user@example.com"}
    ],
    "templateName": "welcome_email",
    "payload": {
      "userName": "John Doe",
      "activationLink": "https://app.example.com/activate?token=abc123"
    },
    "idempotencyKey": "welcome-email-user-123",
    "lang": "en",
    "callbackUrl": "https://your-service.internal/webhooks/email",
    "callbackHeaders": {
      "Authorization": "Bearer your-webhook-secret"
    }
  }'
```

#### Sending an In-App Notification via REST

```bash
curl -X POST "https://notification-service.example.com/in-app-notifications/send?tenant_id=YOUR_TENANT_UUID" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "serviceName": "order-service",
    "recipients": [
      {
        "address": "fcm-device-token-here",
        "externalId": "user-123"
      }
    ],
    "templateName": "order_status",
    "payload": {
      "orderId": "ORD-789",
      "status": "Delivered"
    },
    "idempotencyKey": "order-status-ord789-delivered",
    "lang": "en"
  }'
```

---

### RabbitMQ Integration

For high-throughput scenarios, use RabbitMQ for asynchronous message delivery.

#### Queue Naming Convention

```
notification.{channel}.{tenant-prefix}
```

**Examples:**
- `notification.sms.MYAPP`
- `notification.email.MYAPP`
- `notification.inapp.MYAPP`

#### Message Format

```json
{
  "serviceName": "payment-service",
  "recipients": [
    {
      "address": "+251912345678",
      "externalId": "user-123"
    }
  ],
  "templateName": "payment_confirmation",
  "payload": {
    "amount": "1000.00",
    "currency": "ETB"
  },
  "idempotencyKey": "unique-transaction-id-12345",
  "lang": "en",
  "callbackUrl": "https://your-service.internal/webhooks/notification",
  "callbackHeaders": {
    "Authorization": "Bearer your-webhook-secret"
  }
}
```

#### Python Example (aio-pika)

```python
import json
import asyncio
import aio_pika
from aio_pika import Message, DeliveryMode

async def send_sms_notification():
    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    
    async with connection:
        channel = await connection.channel()
        
        # Declare queue (creates if doesn't exist)
        queue_name = "notification.sms.MYAPP"
        await channel.declare_queue(queue_name, durable=True)
        
        # Prepare notification message
        notification = {
            "serviceName": "payment-service",
            "recipients": [
                {"address": "+251912345678"}
            ],
            "templateName": "payment_confirmation",
            "payload": {
                "amount": "1000.00",
                "currency": "ETB",
                "transactionId": "TXN123456"
            },
            "idempotencyKey": "payment-txn123456",
            "lang": "en"
        }
        
        # Publish message
        message = Message(
            body=json.dumps(notification).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json"
        )
        
        await channel.default_exchange.publish(
            message,
            routing_key=queue_name
        )
        
        print(f"Notification sent to queue: {queue_name}")

# Run the example
asyncio.run(send_sms_notification())
```

#### Node.js Example (amqplib)

```javascript
const amqp = require('amqplib');

async function sendSmsNotification() {
  const connection = await amqp.connect('amqp://guest:guest@localhost:5672');
  const channel = await connection.createChannel();
  
  const queueName = 'notification.sms.MYAPP';
  
  // Ensure queue exists
  await channel.assertQueue(queueName, { durable: true });
  
  const notification = {
    serviceName: 'payment-service',
    recipients: [
      { address: '+251912345678' }
    ],
    templateName: 'payment_confirmation',
    payload: {
      amount: '1000.00',
      currency: 'ETB',
      transactionId: 'TXN123456'
    },
    idempotencyKey: 'payment-txn123456',
    lang: 'en'
  };
  
  // Send message
  channel.sendToQueue(
    queueName,
    Buffer.from(JSON.stringify(notification)),
    { persistent: true, contentType: 'application/json' }
  );
  
  console.log('Notification sent to queue:', queueName);
  
  await channel.close();
  await connection.close();
}

sendSmsNotification().catch(console.error);
```

#### RabbitMQ RPC Mode (Immediate Response)

For scenarios where you need immediate confirmation, use RPC pattern:

```python
import json
import asyncio
import uuid
import aio_pika
from aio_pika import Message, DeliveryMode

async def send_notification_with_response():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    
    async with connection:
        channel = await connection.channel()
        
        # Create callback queue for responses
        callback_queue = await channel.declare_queue(exclusive=True)
        
        # Prepare correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Future to wait for response
        response_future = asyncio.Future()
        
        async def on_response(message: aio_pika.IncomingMessage):
            if message.correlation_id == correlation_id:
                response_future.set_result(json.loads(message.body.decode()))
        
        # Start consuming responses
        await callback_queue.consume(on_response)
        
        # Send notification with RPC headers
        notification = {
            "serviceName": "payment-service",
            "recipients": [{"address": "+251912345678"}],
            "templateName": "payment_confirmation",
            "payload": {"amount": "1000.00", "currency": "ETB"},
            "idempotencyKey": str(uuid.uuid4())
        }
        
        message = Message(
            body=json.dumps(notification).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=correlation_id,
            reply_to=callback_queue.name,  # This enables RPC mode
            content_type="application/json"
        )
        
        await channel.default_exchange.publish(
            message,
            routing_key="notification.sms.MYAPP"
        )
        
        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(response_future, timeout=30.0)
            print(f"Response received: {response}")
            return response
        except asyncio.TimeoutError:
            print("Timeout waiting for response")
            return None

asyncio.run(send_notification_with_response())
```

---

## Notification Channels

### SMS Notifications

#### Notification Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `serviceName` | string | ✅ | Your service identifier (e.g., "payment-service") |
| `recipients` | array | ✅ | List of recipient objects |
| `recipients[].address` | string | ✅ | Phone number (E.164 format recommended) |
| `recipients[].externalId` | string | ❌ | User ID in your system (for tracking) |
| `templateName` | string | ✅ | Name of the SMS template to use |
| `payload` | object | ✅ | Template variables for substitution |
| `idempotencyKey` | string | ✅ | Unique key to prevent duplicates |
| `lang` | string | ❌ | Language code (default: "en") |
| `metadata` | object | ❌ | Custom metadata (passed to callbacks) |
| `callbackUrl` | string | ❌ | Webhook URL for per-request status callbacks |
| `callbackHeaders` | object | ❌ | HTTP headers for callback authentication |

> **Callback Fields:** When `callbackUrl` is provided, the service will send HTTP POST callbacks on successful delivery or permanent failure. The callback URL and headers are stored with the message in the outbox if initial delivery fails, ensuring callbacks are sent even after retry success.

#### Example: SMS Template

```json
{
  "templateName": "otp_verification",
  "tenantId": "123e4567-e89b-12d3-a456-426614174000",
  "serviceName": "auth-service",
  "version": 1,
  "isActive": true,
  "content": {
    "en": "Your verification code is {otpCode}. Valid for {validMinutes} minutes.",
    "am": "የማረጋገጫ ኮድዎ {otpCode} ነው። ለ{validMinutes} ደቂቃ ይሰራል።"
  }
}
```

#### Example: Sending SMS

```json
{
  "serviceName": "auth-service",
  "recipients": [
    {"address": "+251912345678"}
  ],
  "templateName": "otp_verification",
  "payload": {
    "otpCode": "123456",
    "validMinutes": "5"
  },
  "idempotencyKey": "otp-user123-1708123456",
  "lang": "en"
}
```

**Result:** `Your verification code is 123456. Valid for 5 minutes.`

---

### Email Notifications

#### Notification Request Schema

Same as SMS, but `recipients[].address` should be an email address.

#### Example: Email Template

```json
{
  "templateName": "welcome_email",
  "tenantId": "123e4567-e89b-12d3-a456-426614174000",
  "serviceName": "user-service",
  "subject": "Welcome to {companyName}, {userName}!",
  "version": 1,
  "isActive": true,
  "bodyType": "html",
  "body": {
    "en": "<html><body><h1>Welcome {userName}!</h1><p>Thank you for joining {companyName}. Click <a href=\"{activationLink}\">here</a> to activate your account.</p></body></html>",
    "am": "<html><body><h1>እንኳን ደህና መጡ {userName}!</h1><p>{companyName}ን ስለተቀላቀሉ እናመሰግናለን።</p></body></html>"
  },
  "fileUrls": null
}
```

#### Example: Sending Email

```json
{
  "serviceName": "user-service",
  "recipients": [
    {"address": "newuser@example.com", "externalId": "user-456"}
  ],
  "templateName": "welcome_email",
  "payload": {
    "userName": "John Doe",
    "companyName": "Acme Corp",
    "activationLink": "https://app.acme.com/activate?token=xyz789"
  },
  "idempotencyKey": "welcome-user456-20260217",
  "lang": "en"
}
```

---

### In-App Notifications

In-App notifications are delivered via Firebase Cloud Messaging (FCM) to mobile devices or web browsers.

#### Notification Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipients[].address` | string | ✅ | FCM device token |
| `recipients[].externalId` | string | ✅ | User ID in your system (required for in-app) |

#### Example: In-App Template

```json
{
  "templateName": "order_update",
  "tenantId": "123e4567-e89b-12d3-a456-426614174000",
  "serviceName": "order-service",
  "version": 1,
  "isActive": true,
  "body": {
    "en": {
      "title": "Order Update",
      "message": "Your order #{orderId} is now {status}",
      "actionUrl": "https://app.example.com/orders/{orderId}"
    },
    "am": {
      "title": "የትዕዛዝ ዝማኔ",
      "message": "ትዕዛዝዎ #{orderId} አሁን {status} ነው",
      "actionUrl": "https://app.example.com/orders/{orderId}"
    }
  },
  "data": {
    "orderId": "{orderId}",
    "action": "view_order"
  },
  "android": {
    "priority": "high",
    "notification": {
      "sound": "default",
      "channel_id": "orders"
    }
  },
  "apns": {
    "headers": {
      "apns-priority": "10"
    },
    "payload": {
      "aps": {
        "sound": "default",
        "badge": 1
      }
    }
  }
}
```

#### Retrieving User Notifications

Fetch notifications for a user to display in your app:

```bash
# Get notifications for a user
curl -X GET "https://notification-service.example.com/in-app-notifications/by-external-id/user-123?tenant_id=YOUR_TENANT_UUID&page=1&pageSize=20" \
  -H "X-API-Key: your-api-key"
```

#### Get Unread Count

```bash
curl -X GET "https://notification-service.example.com/in-app-notifications/by-external-id/user-123/unread-count?tenant_id=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "externalId": "user-123",
  "unreadCount": 5
}
```

#### Mark Notifications as Read

```bash
# Mark all as read
curl -X PATCH "https://notification-service.example.com/in-app-notifications/by-external-id/user-123/mark-read?tenant_id=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json"

# Mark specific notifications as read
curl -X PATCH "https://notification-service.example.com/in-app-notifications/by-external-id/user-123/mark-read?tenant_id=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "notificationIds": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ]
  }'
```

#### Clear Notifications

```bash
curl -X DELETE "https://notification-service.example.com/in-app-notifications/by-external-id/user-123/clear?tenant_id=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key"
```

---

## Templates

Templates enable reusable, multi-language notification content with variable substitution.

### Template Variables

Use `{variableName}` syntax for placeholders:

```
Hello {userName}, your order #{orderId} has been {status}.
```

### Creating Templates

#### SMS Template

```bash
curl -X POST "https://notification-service.example.com/sms-templates/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "templateName": "order_shipped",
    "tenantId": "YOUR_TENANT_UUID",
    "serviceName": "order-service",
    "version": 1,
    "isActive": true,
    "content": {
      "en": "Hi {customerName}! Your order #{orderId} has been shipped. Track: {trackingUrl}",
      "am": "ሰላም {customerName}! ትዕዛዝ #{orderId} ተልኳል። ይከታተሉ: {trackingUrl}"
    }
  }'
```

#### Email Template

```bash
curl -X POST "https://notification-service.example.com/email-templates/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "templateName": "invoice_ready",
    "tenantId": "YOUR_TENANT_UUID",
    "serviceName": "billing-service",
    "subject": "Invoice #{invoiceNumber} Ready",
    "version": 1,
    "isActive": true,
    "bodyType": "html",
    "body": {
      "en": "<html><body><h1>Invoice Ready</h1><p>Dear {customerName},</p><p>Your invoice #{invoiceNumber} for {amount} is ready.</p><p><a href=\"{invoiceUrl}\">View Invoice</a></p></body></html>"
    }
  }'
```

#### In-App Template

```bash
curl -X POST "https://notification-service.example.com/in-app-templates/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "templateName": "new_message",
    "tenantId": "YOUR_TENANT_UUID",
    "serviceName": "chat-service",
    "version": 1,
    "isActive": true,
    "body": {
      "en": {
        "title": "New Message from {senderName}",
        "message": "{messagePreview}",
        "actionUrl": "/chat/{conversationId}"
      }
    },
    "data": {
      "type": "chat_message",
      "conversationId": "{conversationId}"
    },
    "android": {
      "priority": "high"
    }
  }'
```

### Template Versioning

Templates support versioning. When updating, increment the version number:

```bash
curl -X PUT "https://notification-service.example.com/sms-templates/{template_id}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "templateName": "order_shipped",
    "tenantId": "YOUR_TENANT_UUID",
    "serviceName": "order-service",
    "version": 2,
    "isActive": true,
    "content": {
      "en": "Hi {customerName}! Order #{orderId} shipped via {carrier}. Track: {trackingUrl}",
      "am": "ሰላም {customerName}! ትዕዛዝ #{orderId} በ{carrier} ተልኳል። {trackingUrl}"
    }
  }'
```

---

## Tenant Configuration

### Creating a Tenant

```bash
curl -X POST "https://notification-service.example.com/tenants/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key" \
  -d '{
    "name": "My Application",
    "prefix": "MYAPP",
    "isActive": true,
    "supportedChannels": ["sms", "email", "inapp"],
    "preferedCommunicationMethod": "rabbitmq",
    "callbackUrl": "https://myapp.example.com/webhooks/notification",
    "callbackHeaders": {
      "Authorization": "Bearer webhook-secret-token"
    }
  }'
```

### Tenant Properties

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable tenant name |
| `prefix` | string | Uppercase identifier for RabbitMQ queues (e.g., "MYAPP") |
| `isActive` | boolean | Enable/disable the tenant |
| `supportedChannels` | array | Channels to enable: `["sms", "email", "inapp"]` |
| `preferedCommunicationMethod` | string | `rest`, `rabbitmq`, `kafka`, or `grpc` |
| `callbackUrl` | string | Default webhook URL for notifications |
| `callbackHeaders` | object | HTTP headers for webhook authentication |

---

## Provider Configuration

Each tenant must configure at least one provider per channel they want to use.

### SMS Provider Configuration

#### Afromessage

```bash
curl -X POST "https://notification-service.example.com/tenant-sms-configurations/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenantId": "YOUR_TENANT_UUID",
    "providerName": "afromessage",
    "priority": 1,
    "isActive": true,
    "rateLimitPerMinute": 30,
    "rateLimitPerHour": 500,
    "rateLimitPerDay": 5000,
    "config": {
      "baseUrl": "https://api.afromessage.com/api",
      "apiKey": "your-afromessage-api-key",
      "sender": "YourApp",
      "from": "your-from-id"
    }
  }'
```

#### Kifiya SMS

```bash
curl -X POST "https://notification-service.example.com/tenant-sms-configurations/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenantId": "YOUR_TENANT_UUID",
    "providerName": "kifiya",
    "priority": 2,
    "isActive": true,
    "rateLimitPerMinute": 50,
    "rateLimitPerHour": 800,
    "rateLimitPerDay": 8000,
    "config": {
      "baseUrl": "https://api.kifiya.com/sms",
      "apiKey": "your-kifiya-api-key",
      "sender": "YourApp"
    }
  }'
```

### Email Provider Configuration

#### SMTP

```bash
curl -X POST "https://notification-service.example.com/tenant-email-configurations/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenantId": "YOUR_TENANT_UUID",
    "providerName": "smtp",
    "priority": 1,
    "isActive": true,
    "rateLimitPerMinute": 50,
    "rateLimitPerHour": 800,
    "rateLimitPerDay": 8000,
    "config": {
      "host": "smtp.gmail.com",
      "port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "fromEmail": "noreply@yourcompany.com",
      "fromName": "Your Company",
      "useTls": true,
      "useSsl": false
    }
  }'
```

### In-App Provider Configuration (FCM)

```bash
curl -X POST "https://notification-service.example.com/tenant-inapp-configurations/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenantId": "YOUR_TENANT_UUID",
    "providerName": "fcm",
    "priority": 1,
    "isActive": true,
    "rateLimitPerMinute": 100,
    "rateLimitPerHour": 1000,
    "rateLimitPerDay": 10000,
    "config": {
      "type": "service_account",
      "project_id": "your-firebase-project",
      "private_key_id": "key-id",
      "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
      "client_email": "firebase-adminsdk@your-project.iam.gserviceaccount.com",
      "client_id": "123456789",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token"
    }
  }'
```

### Provider Priority & Failover

When multiple providers are configured for a channel, the system uses them based on priority:

1. **Priority 1** is tried first
2. If it fails, **Priority 2** is tried
3. And so on...

This enables automatic failover between providers.

---

## Processing Modes

The notification service supports two processing modes that determine how failures are handled:

### 1. Fire-and-Forget Mode (Default)

This is the default mode for all REST API calls and RabbitMQ messages without RPC headers.

| Aspect | Behavior |
|--------|----------|
| **Response** | Immediate acknowledgment |
| **On Success** | Notification saved to database, optional callback sent |
| **On Failure** | Message saved to **outbox** for automatic retry |
| **Retry Strategy** | Exponential backoff (5min, 10min, 20min, 40min, 80min) |
| **Max Retries** | 5 attempts (configurable) |
| **Callback** | Sent on success, or after permanent failure |

**Best for:**
- High-throughput scenarios
- Non-blocking operations
- When you want automatic retry handling

```bash
# REST API is always fire-and-forget
curl -X POST "http://localhost:8000/sms-notifications/send?tenant_id=YOUR_TENANT_UUID" \
  -H "Content-Type: application/json" \
  -d '{
    "serviceName": "payment-service",
    "recipients": [{"address": "+251912345678"}],
    "templateName": "payment_confirmation",
    "payload": {"amount": "1000.00"},
    "idempotencyKey": "payment-123",
    "callbackUrl": "https://your-service.internal/webhooks/notification"
  }'
```

### 2. Immediate Mode (RPC)

Enabled via RabbitMQ by including `reply_to` and `correlation_id` message properties.

| Aspect | Behavior |
|--------|----------|
| **Response** | Full delivery result via `reply_to` queue |
| **On Success** | Notification saved to database |
| **On Failure** | Error returned immediately - **no outbox** |
| **Retry Strategy** | Caller is responsible for retry logic |
| **Callback** | Not used (response is synchronous) |

**Best for:**
- Critical notifications requiring confirmation
- When you need to handle retries yourself
- Synchronous workflows

```python
# RabbitMQ RPC Mode - include reply_to and correlation_id
message = Message(
    body=json.dumps(notification).encode(),
    delivery_mode=DeliveryMode.PERSISTENT,
    correlation_id=str(uuid.uuid4()),
    reply_to="my-callback-queue",  # This enables RPC mode
    content_type="application/json"
)
```

### Mode Comparison

| Feature | Fire-and-Forget | Immediate (RPC) |
|---------|-----------------|-----------------|
| Response Time | Immediate | Waits for delivery |
| Outbox Storage | ✅ Yes (on failure) | ❌ No |
| Automatic Retry | ✅ Yes | ❌ No (caller handles) |
| Callback Support | ✅ Yes | ❌ No (uses reply_to) |
| Integration | REST API, RabbitMQ | RabbitMQ only |

---

## Callbacks & Webhooks

The notification service provides comprehensive callback support to notify your application about notification delivery status. Callbacks are sent asynchronously via HTTP POST requests.

### Callback Configuration Levels

Callbacks can be configured at two levels:

| Level | Configuration | Priority |
|-------|---------------|----------|
| **Per-Request** | `callbackUrl` and `callbackHeaders` in notification request | **1st** (highest) |
| **Tenant-Level** | `callbackUrl` and `callbackHeaders` in tenant configuration | **2nd** (fallback) |

Both callbacks are sent if both are configured, ensuring flexibility for microservice architectures.

### When Callbacks Are Sent

#### Immediate Success
When a notification is successfully sent on the first attempt:

```
[Your App] → [Notification Service] → [Provider] ✅ Success
                     │
                     └──→ Callback: status="sent"
```

#### Outbox Retry Success
When a notification fails initially but succeeds after retry:

```
[Your App] → [Notification Service] → [Provider] ❌ Fail → [Outbox]
                                                              │
                                                    (retry after 5 min)
                                                              │
                                        [Provider] ✅ Success ←┘
                                                              │
                     └──────────────────────────────────────→ Callback: status="sent"
```

#### Permanent Failure
When a notification fails after all retry attempts (default: 5):

```
[Your App] → [Notification Service] → [Provider] ❌ Fail → [Outbox]
                                                              │
                                              (retries 1-5 fail)
                                                              │
                     └──────────────────────────────────────→ Callback: status="permanently_failed"
```

### Callback Payload

```json
{
  "idempotencyKey": "payment-txn123456",
  "status": "sent",
  "channel": "sms",
  "recipient": "+251912345678",
  "timestamp": "2026-02-17T10:30:00Z",
  "notificationId": "550e8400-e29b-41d4-a716-446655440000",
  "errorMessage": null,
  "retryCount": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `idempotencyKey` | string | Original idempotency key from your request |
| `status` | string | Delivery status (see below) |
| `channel` | string | Channel: `sms`, `email`, or `inapp` |
| `recipient` | string | Recipient address (phone/email/FCM token) |
| `timestamp` | string | ISO 8601 timestamp of the status change |
| `notificationId` | string | UUID of the notification record (null on immediate failure) |
| `errorMessage` | string | Error details (only on failure) |
| `retryCount` | integer | Number of retry attempts (0 for first-try success) |

### Status Values

| Status | Description | Callback Sent |
|--------|-------------|---------------|
| `sent` | Successfully delivered to provider | ✅ Yes |
| `failed` | Temporary failure, will retry | ❌ No (internal) |
| `permanently_failed` | Failed after max retries | ✅ Yes |

> **Note:** Callbacks are only sent for final states (`sent` or `permanently_failed`), not for intermediate `failed` states during retry.

### Callback HTTP Request

```http
POST /webhooks/notification HTTP/1.1
Host: your-service.example.com
Content-Type: application/json
Authorization: Bearer your-webhook-secret
X-Custom-Header: your-value

{
  "idempotencyKey": "payment-txn123456",
  "status": "sent",
  ...
}
```

### Per-Request Callbacks

Specify callback URL directly in the notification request:

```json
{
  "serviceName": "payment-service",
  "recipients": [{"address": "+251912345678"}],
  "templateName": "payment_confirmation",
  "payload": {"amount": "1000.00"},
  "idempotencyKey": "payment-123",
  "callbackUrl": "https://payment-service.internal/webhooks/sms",
  "callbackHeaders": {
    "Authorization": "Bearer service-secret",
    "X-Service-Name": "payment-service"
  }
}
```

**Use Cases:**
- Different services need different callback endpoints
- Service-specific authentication headers
- Testing/debugging specific notifications

### Tenant-Level Callbacks

Configure default callbacks for all notifications from a tenant:

```bash
curl -X POST "http://localhost:8000/tenants/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application",
    "prefix": "MYAPP",
    "isActive": true,
    "supportedChannels": ["sms", "email", "inapp"],
    "callbackUrl": "https://myapp.example.com/webhooks/notifications",
    "callbackHeaders": {
      "Authorization": "Bearer tenant-webhook-secret"
    }
  }'
```

### Callback Retry Behavior

The notification service implements retry logic for callback delivery:

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 | Immediate | 0s |
| 2 | 1 second | 1s |
| 3 | 2 seconds | 3s |
| 4 | 4 seconds | 7s |

If all callback attempts fail, the failure is logged but does not affect the notification status.

### Implementing a Callback Endpoint

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

WEBHOOK_SECRET = "your-webhook-secret"

@app.post("/webhooks/notification")
async def handle_notification_callback(request: Request):
    # Parse payload
    payload = await request.json()
    
    # Log for debugging
    print(f"Received callback: {payload}")
    
    # Extract key information
    idempotency_key = payload["idempotencyKey"]
    status = payload["status"]
    channel = payload["channel"]
    recipient = payload["recipient"]
    
    # Handle based on status
    if status == "sent":
        # Notification delivered successfully
        await update_notification_status(idempotency_key, "delivered")
        
    elif status == "permanently_failed":
        # Notification failed after all retries
        error_message = payload.get("errorMessage")
        retry_count = payload.get("retryCount", 0)
        await handle_notification_failure(
            idempotency_key, 
            error_message, 
            retry_count
        )
        # Consider: alert, retry via different channel, notify user
    
    return {"status": "received"}
```

### Best Practices for Callbacks

1. **Idempotency**: Handle duplicate callbacks gracefully
   ```python
   if already_processed(idempotency_key):
       return {"status": "already_processed"}
   ```

2. **Quick Response**: Respond quickly (< 5 seconds) to avoid timeouts
   ```python
   # Process async, respond immediately
   background_tasks.add_task(process_callback, payload)
   return {"status": "received"}
   ```

3. **Logging**: Log all callbacks for debugging
   ```python
   logger.info(f"Callback received: {idempotency_key} - {status}")
   ```

4. **Authentication**: Verify callback authenticity
   ```python
   expected_token = request.headers.get("Authorization")
   if expected_token != f"Bearer {WEBHOOK_SECRET}":
       raise HTTPException(status_code=401)
   ```

5. **Error Handling**: Handle missing fields gracefully
   ```python
   notification_id = payload.get("notificationId")  # May be null
   error_message = payload.get("errorMessage", "Unknown error")
   ```

---

## Outbox Pattern & Retry Mechanism

The notification service implements the **Transactional Outbox Pattern** for reliable notification delivery.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NOTIFICATION FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

[1] Request Received
        │
        ▼
[2] Validate & Process
        │
        ├─── ✅ Success ──→ [3a] Save to Notifications Table ──→ [4] Send Callback
        │
        └─── ❌ Failure ──→ [3b] Save to Outbox Table ──→ [Wait for Retry]
                                    │
                                    ▼
                           ┌────────────────────┐
                           │  OUTBOX PROCESSOR  │ (Background Worker)
                           │  ─────────────────  │
                           │  Poll every 30s    │
                           │  Retry with backoff│
                           └────────────────────┘
                                    │
                                    ├─── ✅ Success ──→ Move to Notifications ──→ Send Callback
                                    │
                                    └─── ❌ Max Retries ──→ Mark Permanently Failed ──→ Send Callback
```

### Outbox Tables

Each channel has its own outbox table:

| Channel | Outbox Table | Notification Table |
|---------|--------------|-------------------|
| SMS | `smsOutbox` | `smsNotifications` |
| Email | `emailOutbox` | `emailNotifications` |
| In-App | `inAppOutbox` | `inAppNotifications` |

### Retry Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `OUTBOX_POLL_INTERVAL_SECONDS` | 30 | How often to check for pending messages |
| `OUTBOX_MAX_RETRIES` | 5 | Maximum retry attempts |
| `OUTBOX_BASE_RETRY_DELAY_MINUTES` | 5 | Base delay for exponential backoff |
| `OUTBOX_BATCH_SIZE` | 100 | Messages processed per cycle |

### Exponential Backoff Schedule

| Retry | Delay | Cumulative Time |
|-------|-------|-----------------|
| 1 | 5 min | 5 min |
| 2 | 10 min | 15 min |
| 3 | 20 min | 35 min |
| 4 | 40 min | 1h 15min |
| 5 | 80 min | 2h 35min |

After retry 5, the message is marked as `permanently_failed`.

### Monitoring the Outbox

View pending/failed messages in the outbox:

```bash
# SMS Outbox
curl "http://localhost:8000/sms-outbox/get?status=failed&tenantId=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key"

# Email Outbox
curl "http://localhost:8000/email-outbox/get?status=pending&tenantId=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key"

# In-App Outbox
curl "http://localhost:8000/in-app-outbox/get?tenantId=YOUR_TENANT_UUID" \
  -H "X-API-Key: your-api-key"
```

### Outbox Message Fields

| Field | Description |
|-------|-------------|
| `id` | Unique outbox message ID |
| `recipientNumber/Email/UserId` | Recipient address |
| `messageContent` | Formatted message content |
| `idempotencyKey` | Original idempotency key |
| `templateId` | Associated template |
| `status` | `pending`, `failed`, `permanently_failed` |
| `retryCount` | Number of retry attempts |
| `lastRetryAt` | Timestamp of last retry |
| `lastErrorMessage` | Most recent error message |
| `nextRetryAt` | Scheduled next retry time |
| `providerAttempted` | Provider used in last attempt |
| `callbackUrl` | Per-request callback URL (if provided) |
| `callbackHeaders` | Per-request callback headers (if provided) |

### Manual Retry

Force a retry for a specific outbox message:

```bash
curl -X POST "http://localhost:8000/sms-outbox/{outbox_id}/retry" \
  -H "X-API-Key: your-api-key"
```

This resets the retry count and schedules immediate retry.

---

## API Reference

### Base URL

```
https://notification-service.example.com
```

### Endpoints Summary

#### Tenants
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/get` | List/filter tenants |
| POST | `/tenants/create` | Create tenant |
| PUT | `/tenants/{id}` | Update tenant |
| PATCH | `/tenants/{id}` | Partial update |
| DELETE | `/tenants/{id}` | Delete tenant |
| POST | `/tenants/{id}/regenerate-api-key` | Regenerate API key |

#### SMS
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sms-notifications/send?tenant_id={uuid}` | Send SMS |
| GET | `/sms-notifications/get` | List SMS notifications |
| GET | `/sms-templates/get` | List SMS templates |
| POST | `/sms-templates/create` | Create SMS template |
| PUT | `/sms-templates/{id}` | Update SMS template |
| DELETE | `/sms-templates/{id}` | Delete SMS template |
| GET | `/sms-outbox/get` | View SMS outbox (pending/failed) |

#### Email
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/email-notifications/send?tenant_id={uuid}` | Send email |
| GET | `/email-notifications/get` | List email notifications |
| GET | `/email-templates/get` | List email templates |
| POST | `/email-templates/create` | Create email template |
| PUT | `/email-templates/{id}` | Update email template |
| DELETE | `/email-templates/{id}` | Delete email template |
| GET | `/email-outbox/get` | View email outbox |

#### In-App
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/in-app-notifications/send?tenant_id={uuid}` | Send push notification |
| GET | `/in-app-notifications/getAll` | List all notifications |
| GET | `/in-app-notifications/by-external-id/{id}` | Get user's notifications |
| GET | `/in-app-notifications/by-external-id/{id}/unread-count` | Get unread count |
| PATCH | `/in-app-notifications/by-external-id/{id}/mark-read` | Mark as read |
| PATCH | `/in-app-notifications/{id}/mark-read` | Mark single as read |
| DELETE | `/in-app-notifications/by-external-id/{id}/clear` | Clear notifications |

#### Configurations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenant-sms-configurations/get` | List SMS configs |
| POST | `/tenant-sms-configurations/create` | Create SMS config |
| GET | `/tenant-email-configurations/get` | List email configs |
| POST | `/tenant-email-configurations/create` | Create email config |
| GET | `/tenant-inapp-configurations/get` | List in-app configs |
| POST | `/tenant-inapp-configurations/create` | Create in-app config |

#### Providers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/providers/get` | List available providers |
| POST | `/providers/test` | Test provider configuration |

### Pagination

All list endpoints support pagination:

```
?page=1&pageSize=20&sortBy=createdAt&sortDirection=desc
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `pageSize` | int | 10 | Items per page (max: 100) |
| `sortBy` | string | - | Field to sort by |
| `sortDirection` | string | desc | `asc` or `desc` |
| `search` | string | - | Search text |

### Paginated Response

```json
{
  "items": [...],
  "page": 1,
  "pageSize": 20,
  "totalItems": 150,
  "totalPages": 8,
  "hasNext": true,
  "hasPrevious": false
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "status": 400,
  "code": "VALIDATION_ERROR",
  "message": "Human-readable error message",
  "details": {
    "field": "templateName",
    "reason": "Template name must contain only letters, numbers, underscores, and hyphens"
  },
  "timestamp": "2026-02-17T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not Found |
| 409 | Conflict (duplicate entry) |
| 422 | Unprocessable Entity (validation failed) |
| 429 | Rate Limited |
| 500 | Internal Server Error |

### Common Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `ENTITY_NOT_FOUND` | Resource not found |
| `DUPLICATE_ENTRY` | Resource already exists |
| `INVALID_API_KEY` | API key is invalid or expired |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `PROVIDER_ERROR` | External provider error |
| `TEMPLATE_NOT_FOUND` | Template doesn't exist |

---

## Best Practices

### 1. Idempotency Keys

Always use meaningful, unique idempotency keys:

```
✅ Good: "order-{orderId}-shipped-{timestamp}"
✅ Good: "otp-{userId}-{purpose}-{timestamp}"
❌ Bad:  "random-uuid" (no context)
❌ Bad:  "notification-1" (not unique)
```

### 2. Template Design

- Keep SMS templates under 160 characters when possible
- Use consistent placeholder naming across templates
- Provide translations for all supported languages
- Test templates with various payload lengths

### 3. Error Handling

```python
import requests

def send_notification(payload):
    try:
        response = requests.post(
            "https://notification-service.example.com/sms-notifications/send",
            json=payload,
            headers={"X-API-Key": API_KEY},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            # Duplicate - notification already sent
            print("Notification already sent (idempotency)")
            return None
        elif e.response.status_code == 429:
            # Rate limited - implement backoff
            time.sleep(60)
            return send_notification(payload)
        else:
            raise
```

### 4. Rate Limiting

- Respect rate limits configured per provider
- Implement exponential backoff for 429 responses
- Batch notifications when possible
- Use RabbitMQ for high-volume scenarios

### 5. Callbacks

- Always verify callback authenticity
- Implement idempotent callback handlers
- Log all callback payloads for debugging
- Handle callback failures gracefully

---

## Troubleshooting

### Notification Not Delivered

1. **Check the outbox:**
   ```bash
   curl "https://notification-service.example.com/sms-outbox/get?status=failed&tenantId={uuid}"
   ```

2. **Verify provider configuration:**
   - Check API credentials
   - Verify rate limits aren't exceeded
   - Test provider connectivity

3. **Check template:**
   - Ensure template exists and is active
   - Verify all placeholders are provided in payload

### Duplicate Notifications

- Check idempotency key uniqueness
- Verify your application isn't retrying already-successful requests

### Template Errors

| Error | Solution |
|-------|----------|
| "Template not found" | Check template name matches exactly (case-sensitive) |
| "Missing placeholder" | Ensure all `{placeholders}` have values in payload |
| "Language not found" | Add translation or specify existing language |

### RabbitMQ Issues

1. **Queue not created:**
   - Verify tenant is active
   - Check tenant's `supportedChannels` includes your channel

2. **Messages not consumed:**
   - Check RabbitMQ connection
   - Verify queue name format: `notification.{channel}.{PREFIX}`

### Getting Help

1. Check the OpenAPI documentation: `/docs`
2. Review logs for detailed error messages
3. Contact the platform team with:
   - Tenant ID
   - Request ID / Idempotency Key
   - Timestamp of the issue
   - Full error response

---

## Appendix: Complete Integration Example

### Python SDK Example

```python
"""
Notification Service Client - Python Example
"""
import requests
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid

@dataclass
class Recipient:
    address: str
    external_id: Optional[str] = None

class NotificationClient:
    def __init__(self, base_url: str, api_key: str, tenant_id: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })
    
    def send_sms(
        self,
        template_name: str,
        recipients: List[Recipient],
        payload: Dict[str, Any],
        service_name: str,
        idempotency_key: Optional[str] = None,
        lang: str = "en",
        callback_url: Optional[str] = None,
        callback_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send SMS notification."""
        return self._send_notification(
            channel="sms",
            template_name=template_name,
            recipients=recipients,
            payload=payload,
            service_name=service_name,
            idempotency_key=idempotency_key,
            lang=lang,
            callback_url=callback_url,
            callback_headers=callback_headers
        )
    
    def send_email(
        self,
        template_name: str,
        recipients: List[Recipient],
        payload: Dict[str, Any],
        service_name: str,
        idempotency_key: Optional[str] = None,
        lang: str = "en",
        callback_url: Optional[str] = None,
        callback_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send email notification."""
        return self._send_notification(
            channel="email",
            template_name=template_name,
            recipients=recipients,
            payload=payload,
            service_name=service_name,
            idempotency_key=idempotency_key,
            lang=lang,
            callback_url=callback_url,
            callback_headers=callback_headers
        )
    
    def send_push(
        self,
        template_name: str,
        recipients: List[Recipient],
        payload: Dict[str, Any],
        service_name: str,
        idempotency_key: Optional[str] = None,
        lang: str = "en",
        callback_url: Optional[str] = None,
        callback_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send push notification."""
        return self._send_notification(
            channel="in-app",
            template_name=template_name,
            recipients=recipients,
            payload=payload,
            service_name=service_name,
            idempotency_key=idempotency_key,
            lang=lang,
            callback_url=callback_url,
            callback_headers=callback_headers
        )
    
    def _send_notification(
        self,
        channel: str,
        template_name: str,
        recipients: List[Recipient],
        payload: Dict[str, Any],
        service_name: str,
        idempotency_key: Optional[str],
        lang: str,
        callback_url: Optional[str] = None,
        callback_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        endpoint_map = {
            "sms": "sms-notifications",
            "email": "email-notifications",
            "in-app": "in-app-notifications"
        }
        
        endpoint = endpoint_map[channel]
        url = f"{self.base_url}/{endpoint}/send?tenant_id={self.tenant_id}"
        
        data = {
            "serviceName": service_name,
            "templateName": template_name,
            "recipients": [
                {"address": r.address, "externalId": r.external_id}
                for r in recipients
            ],
            "payload": payload,
            "idempotencyKey": idempotency_key or str(uuid.uuid4()),
            "lang": lang
        }
        
        # Add callback configuration if provided
        if callback_url:
            data["callbackUrl"] = callback_url
        if callback_headers:
            data["callbackHeaders"] = callback_headers
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_user_notifications(
        self,
        external_id: str,
        page: int = 1,
        page_size: int = 20,
        is_read: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Get in-app notifications for a user."""
        url = f"{self.base_url}/in-app-notifications/by-external-id/{external_id}"
        params = {
            "tenant_id": self.tenant_id,
            "page": page,
            "pageSize": page_size
        }
        if is_read is not None:
            params["isRead"] = is_read
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_unread_count(self, external_id: str) -> int:
        """Get unread notification count for a user."""
        url = f"{self.base_url}/in-app-notifications/by-external-id/{external_id}/unread-count"
        params = {"tenant_id": self.tenant_id}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()["unreadCount"]
    
    def mark_as_read(
        self,
        external_id: str,
        notification_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Mark notifications as read."""
        url = f"{self.base_url}/in-app-notifications/by-external-id/{external_id}/mark-read"
        params = {"tenant_id": self.tenant_id}
        data = {"notificationIds": notification_ids} if notification_ids else None
        
        response = self.session.patch(url, params=params, json=data)
        response.raise_for_status()
        return response.json()


# Usage Example
if __name__ == "__main__":
    client = NotificationClient(
        base_url="https://notification-service.example.com",
        api_key="your-api-key",
        tenant_id="your-tenant-uuid"
    )
    
    # Send SMS with callback
    result = client.send_sms(
        template_name="order_confirmation",
        recipients=[Recipient(address="+251912345678", external_id="user-123")],
        payload={
            "orderId": "ORD-12345",
            "totalAmount": "2,500.00 ETB"
        },
        service_name="order-service",
        idempotency_key="order-ORD-12345-confirmation",
        callback_url="https://order-service.internal/webhooks/sms",
        callback_headers={"Authorization": "Bearer order-service-secret"}
    )
    print(f"SMS sent: {result}")
    
    # Send Email with callback
    result = client.send_email(
        template_name="invoice_ready",
        recipients=[Recipient(address="customer@example.com")],
        payload={
            "customerName": "John Doe",
            "invoiceNumber": "INV-001",
            "amount": "5,000.00 ETB"
        },
        service_name="billing-service",
        callback_url="https://billing-service.internal/webhooks/email"
    )
    print(f"Email sent: {result}")
    
    # Get user notifications
    notifications = client.get_user_notifications("user-123")
    print(f"User has {notifications['totalItems']} notifications")
    
    # Get unread count
    unread = client.get_unread_count("user-123")
    print(f"Unread notifications: {unread}")
```

---

## Changelog

### Version 1.1.0 (February 18, 2026)

#### New Features

- **Per-Request Callback URLs**: Added support for `callbackUrl` and `callbackHeaders` in notification requests. Callbacks are sent on successful delivery or permanent failure.

- **Outbox Callback Persistence**: Callback configuration is now stored in the outbox when a notification fails, ensuring callbacks are sent even after successful retries.

- **Dual Callback Support**: Both per-request callbacks and tenant-level callbacks are now sent if both are configured.

#### Changes

- **Processing Mode Clarification**: REST API is now explicitly fire-and-forget mode. Immediate mode (RPC) is only available via RabbitMQ with `reply_to` and `correlation_id`.

- **Database Schema**: Added `callbackUrl` and `callbackHeaders` columns to `smsOutbox`, `emailOutbox`, and `inAppOutbox` tables.

#### Migration Notes

If upgrading from v1.0.0:
1. Run database migrations: `alembic upgrade head`
2. No breaking changes to existing API contracts
3. Existing tenants will continue to use tenant-level callbacks (if configured)

---

*For additional support or questions, please contact the Notification Service team.*

