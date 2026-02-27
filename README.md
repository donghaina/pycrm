# pycrm

A multi-service, event-driven CRM system built with:

* Python (Django + Graphene)
* Apollo Federation Gateway (Node.js)
* Kafka (Redpanda)
* React + TypeScript + Tailwind + Apollo Client
* PostgreSQL

Key features:

* GraphQL Federation (org + crm subgraphs)
* Asynchronous review workflow via Kafka
* Idempotent event consumption
* Multi-tenant authorization via user context
* UUID consistency across DB + services

---

**Architecture Overview**

```
Frontend (React + Apollo Client)
            │
            ▼
Apollo Gateway (:4000)
            │
 ┌──────────┴──────────┐
 ▼                     ▼
org-service         crm-service
(Users/Companies)   (Deals + Kafka publish)
                            │
                            ▼
                       Kafka (Redpanda)
                            │
                            ▼
                      review-worker
                 (asynchronous approval)
                            │
                            ▼
                       PostgreSQL
```

---

**Repo Structure**

```
frontend/
  web/                 # React + TS + Tailwind + Apollo Client

backend/
  org-service/         # Company/User + authorization data (Python)
  crm-service/         # Deal lifecycle + Kafka producer (Python)
  review-worker/       # Kafka consumer for deal review (Python)
  gateway/             # Apollo Federation Gateway (Node)

docker-compose.yml     # One-command orchestration
```

---

**Services**

org-service

* Manages companies (parent + child) and users (roles, tenant)
* Exposes `me`, `company`, `childCompanies` queries
* Source of truth for org visibility

crm-service

* Manages deals
* Mutations: `createDeal`, `submitDealForReview`
* Enforces tenant isolation and role-based write access
* Publishes Kafka event: `deal.review.requested`

review-worker

* Consumes `deal.review.requested`
* Applies auto-approval rule
* Updates deal review fields and stage
* Retry strategy in code:
* In-process retry with backoff (`REVIEW_WORKER_MAX_RETRIES`, `REVIEW_WORKER_RETRY_BACKOFF_SEC`)
* Manual Kafka commit after success/final failure
* Failure records stored in `crm.processed_events` with error details

gateway

* Apollo Federation Gateway
* Composes `org` and `crm` subgraphs
* Forwards `x-user-id` to downstream services

frontend

* React + Apollo Client
* Polling for async state updates
* Pages: deal list, create, detail (status badge + submit action)

---

**Quick Start**

1. Start everything

```bash
docker compose up --build
```

2. Open UI

```
http://localhost:3000
```

UI routes:

* `#/deals` — Deal list
* `#/create` — Create deal
* `#/deal/:id` — Deal detail

UI flow (simplified):

```
Deals List (#/deals)
   ├─ Create → Create Deal (#/create) → Submit → Deal Detail (#/deal/:id)
   └─ Select Deal → Deal Detail (#/deal/:id)
```

---

**Nx Workspace**

This repo is wired as a minimal Nx workspace to run services and tests via Docker Compose.

Install Nx (one-time):

```bash
npm install
```

Common commands (run from repo root):

```bash
# Full stack
npx nx run stack:up
npx nx run stack:down

# Services
npx nx run org-service:serve
npx nx run crm-service:serve
npx nx run review-worker:serve
npx nx run gateway:serve
npx nx run web:serve

# Tests
npx nx run crm-service:test
```

---

**Manual API Verification (Gateway – :4000)**

All requests must include:

```
x-user-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
```

1) Verify authentication context

```bash
curl 'http://localhost:4000/graphql' \
  -H 'content-type: application/json' \
  -H 'x-user-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' \
  --data-raw '{"query":"query { me { id email role companyId } }"}'
```

2) Create a deal

```bash
curl 'http://localhost:4000/graphql' \
  -H 'content-type: application/json' \
  -H 'x-user-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' \
  --data-raw '{"query":"mutation { createDeal(title:\"DemoDeal\", amount:9000, currency:\"CAD\", childCompanyId:\"22222222-2222-2222-2222-222222222222\", createdByUserId:\"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb\") { id reviewStatus stage } }"}'
```

Expected:

```
reviewStatus: NOT_REQUIRED
stage: DRAFT
```

3) Submit for review (async)

```bash
curl 'http://localhost:4000/graphql' \
  -H 'content-type: application/json' \
  -H 'x-user-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' \
  --data-raw '{"query":"mutation { submitDealForReview(dealId:\"<DEAL_ID>\") { id reviewStatus stage } }"}'
```

Immediate response:

```
reviewStatus: PENDING
stage: SUBMITTED
```

4) Poll for final status

```bash
curl 'http://localhost:4000/graphql' \
  -H 'content-type: application/json' \
  -H 'x-user-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' \
  --data-raw '{"query":"query { deal(id:\"<DEAL_ID>\") { id reviewStatus reviewScore reviewReason } }"}'
```

After a few seconds:

* amount < 10000 → APPROVED
* otherwise → REJECTED

---

**Key Design Decisions**

* GraphQL Federation keeps the frontend on a single endpoint.
* Asynchronous review simulates an external approval system and enforces eventual consistency.
* `crm.processed_events` provides idempotency and observability for Kafka consumption.
* Tenant access is enforced server-side using `x-user-id` and org visibility.
* UUIDs are consistent across DB, ORM, and GraphQL.

---

**Testing**

Current:

* `crm-service` unit tests for auth (`get_allowed_company_ids`, `ensure_can_write`).
* `review-worker` unit tests for review decision, idempotency, and retry handling.

Next to test:

* GraphQL mutation permissions with role/tenant boundaries.
* End-to-end async flow with UI polling.

---

**Observability**

```bash
docker compose logs -f gateway
docker compose logs -f crm-service
docker compose logs -f review-worker
```

---

**Environment**

See `.env.example` for configurable ports and service URLs.

---

**Screenshots (Optional)**

![img.png](imgs/img.png)
![img_1.png](imgs/img_1.png)
![img_2.png](imgs/img_2.png)
![img_3.png](imgs/img_3.png)
![img_4.png](imgs/img_4.png)

---

**Production Hardening (Not Implemented)**

* JWT authentication
* Dead-letter queue
* Outbox pattern for reliable publishing
* Metrics + tracing
* Circuit breakers
* Schema registry for event contracts

---

**Summary**

This project demonstrates:

* Multi-service GraphQL Federation
* Event-driven asynchronous processing
* Idempotent Kafka consumer with retries
* Tenant-aware authorization
* Full-stack integration (React → Gateway → Services → Kafka → DB)
