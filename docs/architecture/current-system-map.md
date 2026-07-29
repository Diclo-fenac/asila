# Aasila Current System Map

This document maps the real, verified architecture of Aasila as a multi-tenant, local-first, headless Retrieval-Augmented Generation (RAG) and Model Context Protocol (MCP) knowledge platform.

---

## 1. High-Level Architectural Overview

Aasila is designed around strict tenant isolation enforced at the database engine layer via PostgreSQL Row-Level Security (RLS). All application services, asynchronous background processing workers, and client-facing interfaces (REST API, Typer CLI, and SSE/stdio MCP Server) operate within a transaction-local organization context.

```
       [ Client Layer: REST API / Typer CLI / MCP Clients ]
                                 │
                                 ▼
       [ Security Gate: Principal Injection & RLS Scope ]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [ Synchronous Services ]         [ Async Worker Queue ]
     (Documents, Search, Keys)           (PostgreSQL Queue)
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
      [ PostgreSQL Storage Layer (Shared-Database / RLS) ]
        • platform schema (users, orgs, memberships, keys, audit)
        • app schema (repositories, documents, chunks, jobs, evals)
```

---

## 2. Storage & Database Schema Hierarchy

Aasila divides its database into two distinct PostgreSQL schemas to separate platform administration from tenant application knowledge:

### `platform` Schema
Stores cross-tenant identity, access control, and compliance records:
* **`users`**: Root human user identities.
* **`organizations`**: Tenant boundaries (`id`, `name`, `slug`, `status`). Soft-deletion supported via `status = 'deleted'`.
* **`memberships`**: Maps users to organizations with RBAC roles (`owner`, `admin`, `member`).
* **`api_keys`**: Hashed API keys tied to an organization and user, storing granular scopes (`knowledge:read`, `knowledge:search`, etc.), expiration dates, and revocation timestamps.
* **`service_accounts`**: Machine-to-machine identities scoped to a single organization.
* **`provider_credentials`**: Encrypted API secrets (using AES-GCM via `SecretBox` with `ASILA_MASTER_KEY`) for external embedding/llm providers.
* **`audit_logs`**: Tamper-evident compliance stream recording sensitive actions (`api_key.created`, `organization.deleted`, `mcp.tool_execute`, etc.) with actor ID, target ID, and client IP.

### `app` Schema
Stores tenant-scoped knowledge assets. **Every table in this schema has Row-Level Security (RLS) enabled and forced.**
* **`repositories`**: Logical containers for document collections.
* **`documents`**: Ingested source files and URLs (`source_uri`, `title`, `content_hash`, `status`).
* **`document_chunks`**: Document text fragments with vector embeddings (`pgvector` column with HNSW indexing) and full-text search tokens (`tsvector` English indexing).
* **`ingestion_jobs`**: Durable asynchronous state machine tracking document parsing and embedding progress (`status`, `attempts`, `last_error`, `available_at`).
* **`conversations` & `messages`**: Multi-turn chat histories with AI assistants, including citation tracking.

---

## 3. Asynchronous Worker Queue (PostgreSQL Queue)

Aasila decouples document ingestion from HTTP request lifecycles using Redis and ARQ:
1. **Job Enqueuing**: When a document is uploaded via `POST /api/v1/knowledge/documents`, the API persists the initial `Document` and `IngestionJob` records in PostgreSQL, then pushes the `job_id` to Redis.
2. **Durable Reference**: Jobs store references to `document_id` rather than raw payload content, preventing Redis memory exhaustion on large file uploads.
3. **Worker Processing**: The asynchronous worker (`workers/core.py`) dequeues `job_id`, establishes a transaction-local RLS session for the document's organization, and invokes `service.py`.
4. **Resilience & Circuit Breaking**: Calls to the external Docling OCR/parsing container (`http://docling:5001`) are wrapped in an asynchronous circuit breaker (`@circuit_breaker(failure_threshold=5, recovery_timeout=60)`). If Docling fails or times out, the circuit breaker prevents cascading failures, records the error in `job.last_error`, and marks the job as `failed` after exponential backoff retries.

---

## 4. Client Interfaces & Protocols

Aasila exposes three uniform interfaces over the core services:

| Interface | Transport | Authentication | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **REST API** | HTTP/JSON (`/api/v1/*`) | `X-Asila-API-Key` or `Bearer` token | Full platform administration, ingestion, hybrid search, health diagnostics. |
| **Typer CLI** | Terminal (`asila *`) | Reads `.env` / `ASILA_API_KEY` | Operator runbook automation (`init`, `doctor`, `org`, `key`, `documents`, `jobs`, `audit`, `ingest`, `search`). |
| **MCP Server** | SSE / Stdio (`/mcp`) | `X-Asila-API-Key` / Middleware | AI tool discovery and execution (`asila_search`, `asila_get_document`, `asila_list_documents`, `asila_list_repositories`). |

---

## 5. Security & Isolation Invariants

* **No Caller-Controlled Overrides**: API routes never accept an `organization_id` Query parameter from the client. Tenant context is exclusively derived from the authenticated principal's session (`request.state.organization_id`).
* **Fail-Closed RLS**: PostgreSQL policies assert `organization_id = NULLIF(current_setting('asila.current_organization_id', true), '')`. If the session variable is missing or empty, queries evaluate to zero rows.
* **Encrypted Secrets**: Sensitive API keys for OpenAI/cloud providers are never stored in plaintext. They are encrypted at rest using canonical SecretBox cryptography.
