# ADR 0002: Shared PostgreSQL with Row-Level Security

**Status:** Accepted

Asila core uses shared PostgreSQL tables for application data. Every organization-owned application row has a non-null `organization_id`. PostgreSQL RLS is enabled and forced for those tables.

Requests establish organization context only after authentication and membership validation. The context is set with `SET LOCAL` inside an explicit transaction and is cleared when the transaction ends. The application must not trust organization headers as authorization; headers may only select an organization already authorized for the principal.

Embedding collections are separated by provider/model/dimension so pgvector indexes never mix incompatible dimensions. Dedicated databases remain a future deployment adapter for very large customers, not the core tenancy model.
