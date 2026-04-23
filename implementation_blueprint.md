# implementation_blueprint.md

## 1. Repository Truth Summary

**Brutal Diagnosis:** Asila is currently an **Architectural Shell**. It is a high-fidelity "Skeleton" that defines the directory structure, API contracts, and multi-tenant data boundaries, but **90% of the functional logic is missing or stubbed**.

*   **Maturity:** **Alpha/Prototype**. The backend is a "stub-first" implementation where routing works, but the core engines (RAG, OCR, LLM, Targeting) return mock data or `TODO` markers.
*   **Architecture:** **Intentional but Disconnected**. The multi-tenancy design (using `SET LOCAL` for PostgreSQL RLS) is sophisticated but is not yet fully wired into the SQLAlchemy models or enforced at the database level.
*   **Database Design:** **Incomplete**. It defines 8 relational tables, but the most critical column for the product—the actual **Vector column** in the `embeddings` table—is missing from the code. A 9th table for geo-boundaries is missing entirely despite being required by the UI designs.
*   **Frontend/Backend Alignment:** **Non-existent**. The frontend is 100% missing (only image wireframes exist). The backend provides API endpoints that match the wireframes, but they are not consumed by any code.
*   **Production Readiness:** **Zero**. It lacks password hashing, webhook signature validation, real LLM integration, and a completed schema.

---

## 2. Tech Stack Inventory

### Frontend
*   **Status:** **Missing**.
*   **Planned Framework:** React 18 (Inferred).
*   **Planned Styling:** Tailwind CSS / Material UI.

### Backend
*   **Framework:** FastAPI (version 0.115.0).
*   **API Style:** REST (Dashboard) & Webhook (WhatsApp/Twilio).
*   **Validation:** Pydantic v2.
*   **Auth:** JWT (python-jose) with custom Bearer token middleware.
*   **Middleware Stack:** Custom Tenant Injection (`X-Tenant-Id`) and JWT decoding.

### Database
*   **Engine:** PostgreSQL 15+ with `pgvector` extension.
*   **ORM:** SQLAlchemy 2.0 (Asyncio).
*   **Migration Tool:** Alembic.

### AI / External Integrations
*   **Generation:** Google Gemini 1.5 Pro.
*   **Embeddings:** Gemini 768-dim vectors (`text-embedding-004`).
*   **Multimodal:** Native support for PDF and Image ingestion using Gemini Vision API.
*   **Storage:** Tenant-isolated local file storage for original documents.
*   **Messaging:** Twilio WhatsApp API.

---

## 3. Library and Dependency Inventory

### Core Dependencies
| Package | Purpose | Used In |
| :--- | :--- | :--- |
| `fastapi` | Core web framework. | Everywhere. |
| `sqlalchemy` | Async ORM for DB interaction. | `app/models/`, `app/db/`. |
| `asyncpg` | Async driver for PostgreSQL. | `app/db/session.py`. |
| `pydantic-settings` | Environment variable management. | `app/core/config.py`. |
| `python-jose` | JWT signing and verification. | `app/core/security.py`. |
| `redis` | Caching and rate limiting. | `app/services/cache.py`, `ratelimit.py`. |

### Suspicious / Unused Dependencies
*   **`httpx`**: Included in manifests but primarily used in tests. Should be used for calling LLM APIs.
*   **`python-multipart`**: Installed but only used in `notices.py` for a stubbed file upload.

---

## 4. Database Truth

### Table Inventory

| Table Name | Purpose | Critical Gaps |
| :--- | :--- | :--- |
| `tenants` | Root for multi-tenancy. | None. |
| `notices` | Stores document text and status. | Needs `archived_at` logic. |
| `embeddings` | **Broken**. Stores RAG chunks. | **Missing the `vector` column type.** |
| `users` | Stores citizen interaction data. | Needs better session window tracking. |
| `location_aliases` | Maps user text to canonical areas. | None. |
| `queries` | Audit log of all interactions. | None. |
| `unanswered_queries` | Feedback loop for missing data. | None. |
| `broadcasts` | Logs for outgoing bulk messages. | None. |

### Actual Table Count Required: 9
The system requires **9 tables** for a clean rebuild:
1.  **tenants**
2.  **notices**
3.  **embeddings**
4.  **users**
5.  **location_aliases**
6.  **queries**
7.  **unanswered_queries**
8.  **broadcasts**
9.  **location_boundaries (MISSING)**: Required to store GeoJSON for Map-based Analytics and Broadcast targeting.

---

## 5. Incomplete / Half-Implemented Logic

| File | Issue | Impact |
| :--- | :--- | :--- |
| `services/llm.py` | All functions return hardcoded strings/vectors. | **RAG System is non-functional.** |
| `services/ingestion.py`| OCR is a text placeholder; Chunker is primitive. | **Document upload is a shell.** |
| `services/auth.py` | Returns a hardcoded `Demo Tenant` UUID. | **Security is non-existent.** |
| `services/broadcast.py`| Targeting logic is empty; Twilio call is a stub. | **Cannot send messages.** |
| `db/tenancy.py` | Uses `SET LOCAL` but RLS is not enabled on tables. | **Multi-tenancy is not enforced.** |

---

## 6. Product Module Map

| Module | Maturity | Status |
| :--- | :--- | :--- |
| **Auth & Tenancy** | High (Skeleton) | Logic exists but needs RLS activation. |
| **Ingestion Pipeline**| Low | OCR and Vectorization are stubs. |
| **RAG Query Engine** | Medium | Logic flow is correct, but AI calls are stubs. |
| **Broadcast System** | Low | UI wireframes exist; Backend is a stub. |
| **Analytics Dashboard**| Low | API returns fake data; Frontend is missing. |

---

## 7. Rebuild Blueprint

### Phase 1 — Foundation
*   Initialize Repo with **Poetry**.
*   Setup **Docker Compose** with `ankane/pgvector` and Redis.
*   Implement `BaseSettings` for GCP/AWS keys and DB URLs.

### Phase 2 — Database & Isolation
*   Define all **9 tables**. 
*   **Fix:** Add `embedding: Mapped[Vector] = mapped_column(Vector(768))` to the `Embedding` table.
*   **Security:** Create an Alembic migration that executes `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.

### Phase 3 — Backend Core (The Engines)
*   **LLM Service:** Connected to Google Gemini (Vertex AI). Implemented `extract_document_content` and `generate_response`.
*   **Ingestion:** Implemented `RecursiveChunker` with context enrichment.
*   **Auth:** Implemented `bcrypt` password hashing and JWT generation.

### Phase 3.5 — Enterprise Hardening & Resilience
*   **Background Processing:** Move ingestion pipeline to a background worker (ARQ/Redis).
*   **Structured Logging:** Implement JSON logging for traceability.
*   **Resilience:** Add retry logic for external AI services.

### Phase 3.75 — Intelligence & Trust (The "Smart" Brain)
*   **Hybrid Search:** Combine `pgvector` with PostgreSQL Full-Text Search (TSVector) for high-precision keyword matching.
*   **Explicit Citations:** Modify RAG to return verifiable source links and page numbers.
*   **Language Translation Layer:** Auto-detect and translate citizen queries to English for retrieval, then back to the native language for the response.
*   **Audio RAG:** Native support for WhatsApp Voice Notes via Gemini Audio transcription.
*   **Knowledge Gap Workflow:** Automatic tracking of "I don't know" answers with admin notification.
*   **Crisis Detection:** Redis-based windowing to detect clusters of similar citizen complaints (e.g., "Water Outage").

### Phase 4 — Frontend Core
*   Scaffold React app with **Vite**.
*   Build the `AuthContext` to handle `X-Tenant-Id` headers globally.
*   Implement the **Notice Upload** form with a real progress bar.

### Phase 5 — Business Logic (WhatsApp)
*   Implement the **Twilio Webhook** with signature validation.
*   Use Redis to store the 5-minute **User Location Context**.
*   Implement `retrieval.py` using `pgvector` cosine similarity (`<=>`).

---

## 8. Architectural Risk
*   **Accidental Complexity:** The `SET LOCAL` tenancy approach is powerful but fragile; if a database connection is returned to the pool without being reset, data leakage can occur.
*   **AI Fragility:** The system assumes a 1536-dim vector. If moving to Gemini (`text-embedding-004`), the code must be updated to 768-dim.
*   **Missing Table:** The absence of `location_boundaries` makes the Analytics/Map features impossible to implement without a redesign.

---

## 9. Recommended Clean Architecture

### Keep
*   **FastAPI / Pydantic v2**: Excellent performance and type safety.
*   **Async SQLAlchemy**: Correct choice for high-concurrency webhooks.
*   **Keyword-based Intent Detection**: Great low-cost fallback for LLM routing.

### Rewrite
*   **Authentication**: Delete current `auth.py` stubs; use standard OAuth2 password flow.
*   **Ingestion Pipeline**: Current paragraph-based splitting will lead to poor RAG performance. Use semantic or recursive chunking.

### Remove
*   **Stubbed `Demo Tenant` data**: Replace with a proper `seed.py` script.
*   **Hardcoded vector dimensions**: Make embedding size a config variable.
