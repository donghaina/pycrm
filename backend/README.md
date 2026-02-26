# Backend

Python services + Node gateway.

## Services
- `org-service`: Company/User ownership and auth data (FastAPI + Strawberry)
- `crm-service`: Deal lifecycle + Kafka publish (FastAPI + Strawberry)
- `review-worker`: Kafka consumer for deal review (Python)
- `gateway`: Apollo Gateway (Node)
