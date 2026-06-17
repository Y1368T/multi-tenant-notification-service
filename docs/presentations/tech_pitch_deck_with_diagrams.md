---
marp: true
paginate: true
theme: default
size: 16:9
class: lead
---

<!-- Slide 1 -->
# Multi-Tenant Notification Service
## From Coupled MVC to Hexagonal Resilient Platform

Objective: Adopt a scalable, resilient, testable architecture supporting multi-tenancy & multi-provider delivery.

---

<!-- Slide 2 -->
## Executive Summary

| Aspect | Existing System | New Hexagonal System | Winner |
|--------|----------------|----------------------|---------|
| **Architecture** | MVC + Event-Driven | Hexagonal (Ports & Adapters) + DDD | ✅ New |
| **Database** | MongoDB | PostgreSQL + Redis | ✅ New |
| **Message Queue** | RabbitMQ (per-service queues) | RabbitMQ (per-channel queues) | ✅ New |
| **Code Maintainability** | Medium (coupled) | High (loosely coupled) | ✅ New |
| **Scalability** | Limited (vertical) | Excellent (horizontal) | ✅ New |
| **Testability** | Low (tight coupling) | High (dependency injection) | ✅ New |
| **Performance** | Good | Excellent | ✅ New |
| **Multi-tenancy** | None | Full support | ✅ New |
| **Provider Fallback** | No | Yes (circuit breaker) | ✅ New |
| **Revenue Model** | Cost center | Profit center potential | ✅ New |

Why now: Scale demands, reliability gaps, cost savings , revenue opportunity.

---

<!-- Slide 3 -->
## Existing Architecture (Diagram)

```mermaid
graph TB
    subgraph "Existing System - MVC Pattern"
        RMQ1[RabbitMQ - Multiple Queues]
        subgraph "Per-Service Consumers"
            CONSUMER1[Credit Consumer]
            CONSUMER2[Operation Consumer]
            CONSUMER3[Customer Consumer]
            CONSUMER4[Payment Consumer]
        end
        subgraph "Service Layer - Tightly Coupled"
            CONSUMER_SVC[Consumer Service<br/>• All business logic<br/>• Coupled to MongoDB<br/>• Mixed responsibilities]
        end
        subgraph "Direct Channel Access"
            SMS[SMS Direct Call]
            PUSH[Push Direct Call]
            EMAIL[Email Direct Call]
        end
        MONGO[(MongoDB<br/>• No relations<br/>• No transactions<br/>• Schema-less)]
        PROVIDER[Single SMS Provider<br/>EthioTelecom Only]
    end
    RMQ1 -->|credit_queue| CONSUMER1
    RMQ1 -->|operation_queue| CONSUMER2
    RMQ1 -->|customer_queue| CONSUMER3
    RMQ1 -->|payment_queue| CONSUMER4
    CONSUMER1 --> CONSUMER_SVC
    CONSUMER2 --> CONSUMER_SVC
    CONSUMER3 --> CONSUMER_SVC
    CONSUMER4 --> CONSUMER_SVC
    CONSUMER_SVC -->|Direct DB| MONGO
    CONSUMER_SVC --> SMS
    CONSUMER_SVC --> PUSH
    CONSUMER_SVC --> EMAIL
    SMS --> PROVIDER
    style MONGO fill:#ff9999
    style CONSUMER_SVC fill:#ffcc99
    style PROVIDER fill:#ff6666
```

---

<!-- Slide 4 -->
## Existing Pain Points

- ❌ **N consumer implementations** for N services
- ❌ **Tight coupling** between service layer and MongoDB
- ❌ **No separation** of concerns
- ❌ **Hard to test** due to direct dependencies
- ❌ **Single SMS provider** - no fallback
- ❌ **No multi-tenancy** support
- ❌ **Mixed responsibilities** in consumer service

---

<!-- Slide 5 -->
## New Hexagonal Architecture (Diagram)

```mermaid
graph TB
    subgraph "New System - Hexagonal Architecture"
        RMQ2["RabbitMQ - Channel Queues\nnotification.sms.{tenant}\nnotification.email.{tenant}\nnotification.whatsapp.{tenant}"]
        subgraph "Unified Consumer"
            CONSUMER["Consumer\n• Schema validation\n• Tenant identification\n• Channel routing"]
        end
        subgraph "Core Domain"
            HANDLER["Message Handler\nStrategy Router"]
            subgraph "Channel Handlers"
                SMS_H[SMS Handler]
                EMAIL_H[Email Handler]
                WA_H[WhatsApp Handler]
                INAPP_H[In-App Handler]
            end
        end
        subgraph "Infra Adapters"
            CACHE["Redis\nConfig Cache\nRate Limiting"]
            DB["PostgreSQL\nRelational\nACID\nTemplates"]
        end
        subgraph "Provider Strategies"
            SMS_PROVIDERS["SMS Strategies\nTwilio / AfroMessage\nCircuit Breaker / Fallback"]
            EMAIL_PROVIDERS["Email Strategies\nSendGrid / SMTP / SES"]
            WA_PROVIDERS["WhatsApp API"]
        end
        subgraph "Resilience Layer"
            WORKER["Workers\nEmail / SMS\nRetry / DLQ"]
            OUTBOX["Outbox Tables\nGuaranteed Delivery"]
        end
    end
    RMQ2 --> CONSUMER
    CONSUMER --> HANDLER
    HANDLER --> SMS_H
    HANDLER --> EMAIL_H
    HANDLER --> WA_H
    HANDLER --> INAPP_H
    SMS_H --> CACHE
    EMAIL_H --> CACHE
    SMS_H --> DB
    EMAIL_H --> DB
    SMS_H --> SMS_PROVIDERS
    EMAIL_H --> EMAIL_PROVIDERS
    WA_H --> WA_PROVIDERS
    SMS_PROVIDERS --> OUTBOX
    EMAIL_PROVIDERS --> OUTBOX
    WORKER --> OUTBOX
    style CACHE fill:#99ff99
    style DB fill:#9999ff
    style WORKER fill:#ffcc99
    style SMS_PROVIDERS fill:#66ff66
```

---

<!-- Slide 6 -->
## End-to-End Sequence (Reliability)

```mermaid
sequenceDiagram
    participant EXT as External System
    participant RMQ as RabbitMQ
    participant CONS as Consumer
    participant HAND as Handler
    participant CH as Channel Handler
    participant REDIS as Redis
    participant DB as Postgres
    participant PROV as Provider
    participant OUTBOX as Outbox
    participant WORKER as Worker
    participant DLQ as DLQ
    participant CALLBACK as Callback
    EXT->>RMQ: Publish Notification
    RMQ->>CONS: Consume
    CONS->>CONS: Validate & Identify Tenant
    CONS->>HAND: Route (channel, tenant)
    HAND->>CH: Invoke Channel Handler
    CH->>REDIS: Get Config
    alt Config Cache Hit
        REDIS-->>CH: Config
    else Miss
        CH->>DB: Load Config
        DB-->>CH: Config
        CH->>REDIS: Cache Config
    end
    CH->>DB: Load Template
    DB-->>CH: Template
    CH->>PROV: Send
    alt Success
        PROV-->>CALLBACK: Success Callback
    else Failure
        PROV->>OUTBOX: Persist Failed Attempt
    end
    loop Worker Retries
        WORKER->>OUTBOX: Fetch Pending
        WORKER->>PROV: Retry Send
        alt Success
            PROV-->>CALLBACK: Success Callback
        else Max Retries
            WORKER->>DLQ: Move to DLQ
        end
    end
```

---
<!-- Slide 7 -->
## Key Improvements 

- ✅ **Single consumer** for all services
- ✅ **Loose coupling** via dependency injection
- ✅ **Clear separation** of concerns (Domain, Application, infrastructure)
- ✅ **Highly testable** with interface mocking
- ✅ **Multi-provider** with automatic fallback
- ✅ **Full multi-tenancy** support
- ✅ **Worker services** for guaranteed delivery
- ✅ **Circuit breakers** for resilience
  
<!-- Slide 8 -->
## Message Contract & Queue Naming

**Queue Pattern:** `notification.{channel}.{tenant}`
Examples: `notification.sms.qena`, `notification.email.qena`

```json
{
  "serviceName": "payment",
  "recipient": { "address": "0913327219" },
  "templateName": "transaction_alert",
  "payload": {
    "transactionNo": "TXN123456",
    "amount": "1000.00",
    "accountNumber": "1000022333",
    "balance": "5000.00",
    "transactionType": "CREDIT"
  },
  "idempotencyKey": "payment-txn-123456",
  "lang":"en",
  "api-keys":"qena_ndjnkndkmldmAnbdn6999bjbntcf_keys"
}
```

---

<!-- Slide 98 -->
## Data & Multi-Tenancy

- Postgres: tenants, templates (JSONB multi-language), outbox, callbacks
- Constraints & FKs guarantee integrity; unique (tenant_id, template_key)
- Redis: hot config, rate limiting, performance (10–20ms access)
- Eager includes prevent N+1 (template, template.tenant)
  
---

<!-- Slide 10 -->
## Scalability, Reliability & Resilience Components

- Outbox pattern: eventual consistency & guaranteed delivery
- Workers: exponential backoff retries; DLQ for permanent failures
- Circuit breakers + provider fallback chains
- Idempotency keys & structured audit logging
- Per-channel queue scaling; independent autoscaling per channel
<!-- Slide 11 -->
## Security & Compliance

- Multi-tenant API keys (`nt_{tenant}_{secret}`); strict isolation
- Per-tenant rate limits; PII masking & encrypted at rest
- Audit trails + correlation IDs; GDPR/SOC2-ready retention
- Circuit breakers reduce abuse impact

---

<!-- Slide 12 -->
## Migration Plan (3 Phases)

1. Phase 1: Roll out Repository + UoW + Provider Strategies + Redis config
2. Phase 2: Pilot on SMS then In-APP Notification
3. Phase 3: Enable Outbox + Workers + DLQ dashboards; extend to other channels

---

<!-- Slide 13 -->
## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration complexity | Phased rollout, feature flags |
| Query performance | Indexes, query plan review, tracing |
| Provider limits/outages | Rate limiting + fallback chain + circuit breaker |
| Cache staleness | TTL, cache-aside, invalidation hooks | 
---

<!-- Slide 14 -->
## Team Impact & Changes

- Publish using channel queues + standard message contract
- Use Repo + Spec + UoW + BaseService patterns for data access
- Add metrics/traces; follow retry & idempotency guidelines
- DevOps: autoscaling policies, dashboard for outbox/DLQ
  
---

## Thank You
