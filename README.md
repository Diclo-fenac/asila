# Aasila: Verified Information Hub for Governments

Aasila is a high-performance, secure, and multi-tenant AI platform designed for government-scale verified information management. It leverages **Retrieval-Augmented Generation (RAG)**, **Geospatial Intelligence**, and **Isolated Tenant Architectures** to provide a trusted "Single Source of Truth."

## 🚀 Key Features

*   **Secure Multi-Tenancy:** Hard isolation via PostgreSQL schemas (one database per tenant), ensuring strict data privacy and regulatory compliance.
*   **Advanced RAG Pipeline:** Integration with **Google Gemini 1.5 Pro** and **pgvector** for semantic search and grounded AI responses.
*   **Geospatial Intelligence:** Built-in **PostGIS** support for location-aware queries and boundary-based data filtering.
*   **Automated Tenant Provisioning:** One-click tenant onboarding with automated database creation and schema migration.
*   **Asynchronous Processing:** Decoupled document ingestion and embedding generation using **arq** background workers.
*   **Modern Frontend:** High-speed dashboard built with **React, TypeScript, and Zustand**, featuring real-time analytics and multi-tenant switching.

---

## 🛠 Tech Stack

-   **Language:** Python 3.11+ (Backend), TypeScript (Frontend)
-   **Backend Framework:** FastAPI
-   **Database:** PostgreSQL with `pgvector` and `PostGIS`
-   **ORM:** SQLAlchemy (Async)
-   **Migrations:** Alembic (Dual-migration strategy)
-   **Task Queue:** `arq` (Redis-backed)
-   **Frontend:** React 18, Vite, Tailwind CSS, Zustand
-   **AI Services:** Google Gemini 1.5 Pro, Google Generative AI (SDK)
-   **Infrastructure:** Docker, Docker Compose

---

## 🚦 Prerequisites

Before you begin, ensure you have the following installed:
-   **Python 3.11 or 3.12**
-   **Node.js 18+** & **npm**
-   **Docker & Docker Compose**
-   **uv** (recommended for Python dependency management)
-   **Google Gemini API Key** (for RAG and extraction)

---

## 🏁 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/Diclo-fenac/asila.git
cd asila
```

### 2. Infrastructure Setup (Docker)
Start the required infrastructure services (PostgreSQL with Vector/PostGIS and Redis):
```bash
docker-compose -f deployments/docker/docker-compose.yml up -d
```

### 3. Backend Environment Setup
Create a `.env` file in the root directory:
```bash
cp .env.example .env # Or create manually
```

**Required Variables:**
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Platform DB connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/asila_platform` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `GOOGLE_API_KEY` | Your Gemini API Key | `AIzaSy...` |
| `AUTH0_DOMAIN` | Auth0 Tenant Domain | `dev-xxx.auth0.com` |
| `AUTH0_AUDIENCE` | Auth0 API Audience | `https://api.asila.gov` |

### 4. Install Dependencies
```bash
# Backend
uv sync

# Frontend
cd frontend
npm install
cd ..
```

### 5. Database Initialization & Migrations
Aasila uses a dual-migration strategy. You must initialize the platform and the tenant template.

```bash
# 1. Run the bootstrap script to create databases and enable extensions
uv run python scripts/bootstrap_tenant.py

# 2. Run Platform Migrations
uv run alembic -c alembic.platform.ini upgrade head

# 3. Apply the tenant schema to the template database
# (All new tenants are cloned from this template)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/asila_schema_template
uv run alembic -c alembic.tenant.ini upgrade head
```

### 6. Start the Application
You need to run three components in separate terminals:

**Terminal 1: API Server**
```bash
uv run uvicorn apps.api.main:app --reload
```

**Terminal 2: Background Worker**
```bash
uv run arq workers.main.WorkerSettings
```

**Terminal 3: Frontend Dev Server**
```bash
cd frontend
npm run dev
```

---

## 🏗 Architecture Overview

### Directory Structure
```
├── apps/
│   └── api/                # FastAPI Entry point & Routes
├── core/
│   ├── config/             # Pydantic Settings
│   ├── database/           # Platform & Tenant session engines
│   ├── security/           # JWT Auth & Rate Limiting
│   └── tenant/             # Tenant resolver (Redis-backed)
├── domain/                 # Business Logic & Models
│   ├── platform/           # Platform-level (Tenants, etc.)
│   └── tenant/             # Tenant-level (Docs, Chunks, Embeddings)
├── services/               # Cross-cutting services
│   ├── ingestion/          # Recursive Chunker & Pipeline
│   ├── embeddings/         # Vector generation
│   └── retrieval/          # Hybrid RAG search
├── infra/                  # External Adapters (Gemini, Storage)
├── migrations/             # Alembic Migrations (Platform vs Tenant)
├── tests/                  # Pytest suite
└── frontend/               # React Dashboard & Chat UI
```

### The Ingestion Lifecycle
1.  **Request:** User uploads a document via `POST /documents`.
2.  **Storage:** The file is saved to local storage (or S3 adapter).
3.  **Extraction:** `Gemini 1.5 Pro` parses the file (PDF/Image) into structured Markdown.
4.  **Chunking:** `RecursiveChunker` splits text at semantic boundaries (Paragraph -> Sentence -> Word).
5.  **Vectorization:** `text-embedding-004` generates high-dimensional vectors for every chunk.
6.  **Persistence:** Chunks and Vectors are stored in the **Tenant-specific database**.

### Multi-Tenancy Resolution
Aasila uses a **Database-per-Tenant** isolation model:
-   **Resolver:** Middleware identifies the tenant from the request headers/subdomain.
-   **Cache:** Database connection strings are cached in **Redis** for sub-millisecond resolution.
-   **Isolation:** The `get_tenant_db` dependency dynamically switches SQLAlchemy engines per request.

---

## 🧪 Testing

We use `pytest` with `pytest-asyncio` for comprehensive testing of RAG pipelines and isolation logic.

```bash
# Run all tests with dummy environment variables
GOOGLE_API_KEY=dummy \
DATABASE_URL=postgresql+asyncpg://u:p@h/d \
REDIS_URL=redis://h \
AUTH0_DOMAIN=d \
AUTH0_AUDIENCE=d \
uv run pytest tests/
```

### Key Test Suites:
-   `test_document_ingestion.py`: Verifies the recursive chunking and Gemini integration.
-   `test_tenant_provisioning.py`: Ensures databases are correctly created from templates.
-   `test_tenant_resolver.py`: Tests the Redis-backed tenant switching logic.

---

## 🚀 Deployment

### Docker Deployment (Recommended)
The project includes a production-ready `docker-compose` configuration.

```bash
docker build -t asila-api -f deployments/docker/Dockerfile .
docker-compose -f deployments/docker/docker-compose.yml up -d
```

### Production Considerations
-   **Database:** Use a managed PostgreSQL service (e.g., AWS RDS, GCP Cloud SQL) with `pgvector` enabled.
-   **Storage:** Swap `LocalStorageService` for an S3-compatible adapter.
-   **SSL:** Use a reverse proxy like Nginx or Traefik for TLS termination.

---

## 🛠 Available Scripts

| Command | Description |
|---------|-------------|
| `uv run python scripts/bootstrap_tenant.py` | Initializes Platform and Template databases |
| `uv run alembic -c alembic.platform.ini upgrade head` | Migrates the Platform control plane |
| `uv run alembic -c alembic.tenant.ini upgrade head` | Migrates the current database (set via env) |
| `uv run arq workers.main.WorkerSettings` | Starts the background worker |
| `npm run build` | Builds the frontend for production |

---

## ❓ Troubleshooting

**PostgreSQL Extension Errors**
-   Ensure your Postgres user has superuser privileges to run `CREATE EXTENSION IF NOT EXISTS vector`.
-   If running locally on macOS, use `brew install pgvector`.

**Gemini API Failures**
-   Verify your `GOOGLE_API_KEY` has the "Generative AI API" enabled in the Google Cloud Console.

**Migration Mismatch**
-   If you see "Target database is not at revision...", ensure you are running the correct alembic config file (`.platform.ini` vs `.tenant.ini`).
