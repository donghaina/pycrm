# crm-service

Owns Deal lifecycle and publishes Kafka review events. Exposes a GraphQL subgraph.

Target features:
- createDeal
- submitDealForReview (sets PENDING + publish event)
- deals/deal queries with authorization
