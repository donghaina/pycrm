# org-service

Owns Company/User and org hierarchy data. Exposes a GraphQL subgraph.

Target schema:
- Company (parent/child)
- User (role, company)

Responsibilities:
- Provide org visibility rules
- Enforce authorization in resolvers
