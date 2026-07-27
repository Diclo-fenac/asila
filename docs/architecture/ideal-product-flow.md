# Aasila Ideal Product Flow & Tenant Lifecycle

This document defines the end-to-end lifecycle of an Aasila deployment, mapping the journeys of the five core personas from zero-installation bootstrapping to daily multi-tenant AI operations.

---

## 1. Core Personas

1. **Platform Operator**: Responsible for deploying, monitoring, and scaling the underlying Docker/PostgreSQL/Redis/Docling infrastructure.
2. **Organization Owner**: Responsible for administrative governance of a specific tenant, managing memberships, generating and rotating API keys, and auditing security logs.
3. **Knowledge Contributor**: Responsible for uploading documents, creating repositories, and monitoring background ingestion pipelines.
4. **Knowledge Consumer**: Responsible for searching and retrieving verified, source-grounded information from the platform.
5. **AI / MCP Client**: Autonomous agents or IDE assistants (e.g., Claude Desktop, Cursor) discovering and calling MCP tools to answer complex user queries.

---

## 2. End-to-End Lifecycle Flow

```
[Phase 1: Bootstrapping] ──► [Phase 2: Org Setup] ──► [Phase 3: Ingestion] ──► [Phase 4: Retrieval & MCP]
  Operator runs compose         Owner runs init          Contributor ingests     Consumer / AI queries
  & verifies health             & provisions keys        docs & checks jobs      hybrid search & tools
```

### Phase 1: Zero-Installation & Infrastructure Bootstrapping
* **Actor**: Platform Operator
* **Action**:
  1. The operator clones the Aasila repository and runs `docker compose up -d` to launch PostgreSQL (with `pgvector`), Redis, Ollama, Docling, and the FastAPI backend.
  2. The operator runs `asila doctor` (or `asila status`) to verify that all required services are healthy and responsive.
  3. The operator generates `.env` with random development secrets (`ASILA_MASTER_KEY`, `ASILA_SETUP_TOKEN`, `POSTGRES_PASSWORD`).
* **Outcome**: A secure, isolated runtime stack ready for multi-tenant provisioning.

### Phase 2: Tenant Provisioning & Access Governance
* **Actor**: Organization Owner
* **Action**:
  1. Using the setup token, the owner executes `asila init --org "Acme Corp" --non-interactive` (or `POST /api/v1/setup`). This creates the root human user, the primary organization, and returns an initial Owner API key.
  2. The owner creates specialized API keys with least-privilege scopes using `asila key create --name "CI-Ingestion" --scopes "documents:write,knowledge:read"`.
  3. For automated systems, the owner creates Service Accounts (`POST /api/v1/service-accounts`) scoped strictly to their organization.
* **Outcome**: Tenant isolation boundaries are established in PostgreSQL with tamper-evident audit logging active.

### Phase 3: Knowledge Ingestion & Durable Processing
* **Actor**: Knowledge Contributor
* **Action**:
  1. The contributor creates a logical repository (`POST /api/v1/knowledge/repositories`).
  2. Using the CLI, the contributor uploads markdown, PDF, or text files: `asila ingest --path ./docs/ --repo-id <repo_id>`.
  3. The backend immediately returns a `job_id` and queues the parsing task in Redis.
  4. The contributor monitors progress using `asila jobs get <job_id>` or `asila ingest-status <document_id>`.
  5. Behind the scenes, the ARQ worker invokes the Docling OCR service (protected by circuit breakers) to extract text, chunks the content, generates embeddings via Ollama/OpenAI, and stores vector and full-text indexes in PostgreSQL.
* **Outcome**: Documents are fully indexed and ready for low-latency retrieval.

### Phase 4: Hybrid Search & AI MCP Integration
* **Actor**: Knowledge Consumer & AI / MCP Client
* **Action**:
  1. **Human Consumer**: Exercises `asila search --query "multi-tenant RLS" --mode hybrid --limit 5` from the terminal.
  2. **AI Assistant**: Connects to `/mcp` via SSE or `asila mcp-stdio`. Exercises `tools/list` to discover `asila_search`, `asila_get_document`, and `asila_list_documents`.
  3. When the user asks a question, the AI assistant invokes `asila_search(query="security gate", mode="hybrid")`.
  4. Aasila executes Reciprocal Rank Fusion (RRF), combining exact keyword matches (`tsvector`) with semantic similarity (`pgvector`), filtered strictly by the client's `organization_id`.
  5. The assistant retrieves the exact source document using `asila_get_document(document_id=...)` and generates a verified, source-grounded response with citations.
* **Outcome**: Flawless, secure, and verifiable knowledge retrieval without data leakage across tenants.

---

## 3. Compliance & Continuous Audit Verification
At any point in the lifecycle, the Organization Owner or security auditor can execute `asila audit verify` (or `GET /api/v1/audit`) to inspect a chronological stream of tamper-evident security events, ensuring total visibility into key creations, rotations, deletions, and MCP tool invocations.
