# Asila implementation status

As of 2026-07-23, the product is a modular, API-first knowledge platform with one supported shared-schema architecture.

## Current phases

| Phase | Status | Delivered |
|---|---|---|
| 0. Product boundary | Complete | Open-source, self-hostable knowledge/MCP scope; frontend and government workflows are outside core. |
| 1. Data and tenancy | Complete | Shared `platform`/`app` schemas, mandatory RLS, transaction-local organization context, organization-aware foreign keys. |
| 2. Identity and authorization | Complete | OIDC validation, API keys, memberships, owners/admins, service accounts, soft deletion, audit logs, encrypted provider credentials. |
| 3. Ingestion and AI | Complete for text v1 | Deterministic chunking, source/hash idempotency, durable ARQ embedding jobs, retry/backoff, Ollama/Gemini/OpenAI-compatible adapters. |
| 4. Retrieval and conversations | Complete for v1 | PostgreSQL FTS, pgvector hybrid search, repository filtering, citations, conversation history, optional generation. |
| 5. MCP and CLI | Complete for v1 | Authenticated SSE MCP search/retrieval tools, `asila init`, `ingest`, `search`, and `status`. |
| 6. Deployment and operations | Complete for local release candidate | Compose Postgres/Redis/migrations/API/worker, local AI profile, readiness endpoint, request IDs, documentation, and tests. |

## Explicit next phase

The next implementation phase is scale and integration hardening: streaming uploads for large files, repository/connector synchronization and deletion manifests, real PostgreSQL RLS isolation tests, dimension-specific vector indexes, MCP transport integration tests, rate/latency metrics, Kubernetes manifests, and generated SDK packaging.

The current core test gate passes: `80 passed` with no skipped legacy tests.
