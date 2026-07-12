<div align="center">
  <h1>🚀 Asila</h1>
  <p><b>The Developer-First Enterprise Knowledge Hub.</b></p>
  <p>
    <a href="https://github.com/Diclo-fenac/asila/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
    <img src="https://img.shields.io/badge/Protocol-MCP-purple.svg" alt="MCP Protocol">
  </p>
</div>

**Asila** is a developer-first enterprise knowledge hub designed with the "Connect and Play" philosophy. It completely bypasses traditional web dashboard interfaces in favor of pure, programmatic CLI/API ingestion and native Model Context Protocol (MCP) integration. This allows AI assistants and IDEs to seamlessly index and query your internal knowledge base.

## Table of Contents
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Key Features

- **Native MCP Integration**: Plug your enterprise knowledge base directly into Claude Desktop or Cursor via Server-Sent Events (SSE).
- **True Multi-Tenancy**: Tenant data isolation enforced cryptographically at the database level using PostgreSQL Row-Level Security (RLS).
- **Frictionless Ingestion**: Built-in CLI wrapper (`asila.sh`) respects `.gitignore` natively to effortlessly sync local repositories and documents.
- **Robust Background Processing**: Uses `arq` and Redis to handle heavy ingestion jobs asynchronously with exponential backoff and a Dead Letter Queue (DLQ).
- **Hybrid Search**: Leverages `pgvector` for high-performance semantic search over enterprise documents.

---

## Tech Stack

- **Language**: Python 3.11+ / TypeScript
- **Framework**: FastAPI (Backend) / React 19 + Vite (Frontend)
- **Database**: PostgreSQL 16 with `pgvector`
- **Caching & Queues**: Redis
- **Background Jobs**: Arq
- **Secrets Management**: HashiCorp Vault
- **Package Manager**: `uv` (Python) / `npm` or `yarn` (Frontend)
- **Deployment**: Docker & Docker Compose

---

## Prerequisites

- **Docker & Docker Compose**: Essential for running PostgreSQL, Redis, and Vault.
- **Python 3.11+**: Required for local backend development.
- **uv**: The ultra-fast Python package installer (recommended) or `pip`.
- **Node.js 20+**: Required if developing the React frontend.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Diclo-fenac/asila.git
cd asila
```

### 2. Environment Setup

Copy the example environment files for both the root and the backend:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Ensure your root `.env` looks something like this:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/asila_platform` |
| `REDIS_URL` | Redis connection for caching and Arq | `redis://localhost:6379/0` |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD`| PostgreSQL password | `postgres` |
| `AUTH0_DOMAIN` | For frontend/backend auth | `your-domain.auth0.com` |

### 3. Database & Services Setup (Docker)

To run the full stack (Database, Redis, Vault, Backend API, and Worker) seamlessly:

```bash
docker compose up -d
```

### 4. Local Development (Running without Docker)

If you prefer to run the backend and frontend locally on your host machine for development:

**Start Infrastructure Dependencies:**
```bash
docker compose up -d postgres redis vault
```

**Install Backend Dependencies (using uv):**
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
uv pip install -e ".[dev]"
```

**Run Database Migrations:**
```bash
# Run migrations for the platform schema
alembic -c alembic.platform.ini upgrade head

# Run migrations for the shared tenant schemas
alembic -c alembic.shared.ini upgrade head
```

**Start the FastAPI Server:**
```bash
uvicorn api.main:app --reload --port 8000
```

**Start the Background Worker:**
```bash
# In a new terminal
cd backend
source .venv/bin/activate
arq workers.main.WorkerSettings
```

**Start the Frontend (Optional):**
```bash
cd frontend
npm install
npm run dev
```

The API will be available at [http://localhost:8000/docs](http://localhost:8000/docs) and the frontend at [http://localhost:5173](http://localhost:5173).

---

## Architecture

### Directory Structure

```text
asila/
├── backend/                 # FastAPI application
│   ├── api/                 # REST controllers & MCP SSE routes
│   │   ├── main.py          # FastAPI application entry point
│   │   └── routes/          # API route definitions
│   ├── core/                # TenancyMiddleware, security, config
│   ├── domain/              # Pydantic models & business logic
│   ├── infra/               # Database schemas and connections
│   ├── services/            # Core logic (Ingestion, Search)
│   ├── worker/              # Arq background job tasks
│   ├── migrations/          # Alembic migrations
│   └── pyproject.toml       # Python dependencies
├── frontend/                # React 19 + Vite dashboard
│   ├── src/                 # React components and hooks
│   └── package.json         # Frontend dependencies
├── docs/                    # Architecture diagrams and documentation
├── storage/                 # Local docker volumes
├── asila.sh                # CLI ingestion wrapper
└── docker-compose.yml       # Docker orchestration
```

### Request Lifecycle

1. Request hits FastAPI router (`backend/api/main.py`)
2. `TenancyMiddleware` inspects headers for `asila-api-key`.
3. Middleware maps the API key to a specific tenant ID and injects it into the request context.
4. Route handler invokes the appropriate Service layer.
5. Service queries PostgreSQL (`infra/`), automatically scoping the query to the tenant using Row-Level Security (RLS) via SQLAlchemy.
6. For heavy ingestion tasks, the Service enqueues a job to Redis.
7. Arq `worker/` picks up the job and processes documents via LLM/embeddings in the background.

### Key Components

**Native MCP Integration (`backend/api/routes/mcp.py`)**
- Exposes Model Context Protocol endpoints using Server-Sent Events (SSE).
- Allows IDEs to send messages to the server and receive semantic context dynamically.

**Multi-Tenancy (`backend/core/`)**
- API Keys are validated against the `asila_platform` database.
- Queries are executed against the `asila_shared` database.
- RLS policies ensure `tenant_a` cannot mathematically read rows belonging to `tenant_b`.

**CLI Ingestion (`asila.sh`)**
- Recursively walks a project directory, respecting `.gitignore`.
- Packages files into a payload and ships them to the FastAPI ingestion route.

---

## Required Environment Variables

To run the backend, create a `.env` file in the `backend/` directory with the following variables. Do **not** commit this file.

| Variable | Description | Required? | Example |
|----------|-------------|-----------|---------|
| `ENVIRONMENT` | `development`, `staging`, or `production` | Yes | `development` |
| `ASILA_MASTER_KEY` | Key for admin tenant provisioning | Yes | `openssl rand -hex 32` |
| `PLATFORM_API_KEY` | Generic platform API key | Yes | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `REDIS_URL` | Redis connection string | Yes | `redis://localhost:6379/0` |
| `GOOGLE_API_KEY` | Gemini API Key for LLM operations | Yes | `AIzaSy...` |
| `SECRET_KEY` | Session/JWT signing key | Optional | `openssl rand -hex 32` |
| `VAULT_URL` | HashiCorp Vault URL | Optional | `http://localhost:8200` |
| `VAULT_TOKEN` | HashiCorp Vault Token | Optional | `root` |

---

## Available Scripts

### Backend (Run inside `backend/`)

| Command | Description |
|---------|-------------|
| `uvicorn api.main:app --reload` | Start FastAPI development server |
| `arq workers.main.WorkerSettings` | Start Arq background worker |
| `pytest` | Run the Python test suite |
| `alembic -c alembic.platform.ini upgrade head` | Run platform database migrations |

### Frontend (Run inside `frontend/`)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build TypeScript and Vite for production |
| `npm run lint` | Run ESLint |

### Root CLI Wrapper

| Command | Description |
|---------|-------------|
| `./asila.sh ingest` | Ingest current directory into Asila |

---

## Testing

### Running Tests

We use `pytest` for the backend. Make sure your database and Redis are running.

```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest

# Run tests with output
pytest -s -v

# Run specific test file
pytest tests/test_search.py
```

### Test Structure

```text
backend/
├── tests/
│   ├── test_search.py        # Semantic search logic tests
│   ├── test_insert.py        # Database insertion and RLS tests
│   ├── test_mcp_client.py    # MCP protocol integration tests
│   └── test_session.py       # Session management tests
```

---

## Deployment

Asila is designed to be deployed using Docker. 

### Docker (Production / VPS)

1. Clone the repository on your server.
2. Update the `.env` variables with strong passwords and production URLs.
3. Build and launch the containers:

```bash
# Build images
docker compose build

# Run detached
docker compose up -d
```

This will automatically spin up:
- The FastAPI Backend on port `8000`
- The Arq Background Worker
- The PostgreSQL Database
- Redis
- Hashicorp Vault

### Connecting to IDEs (MCP)

To connect an AI assistant to your production server:

**Cursor Configuration**
1. Open Cursor Settings > **Features** > **MCP**
2. Add new server (Type: **SSE**)
3. URL: `https://your-production-url.com/mcp`
4. Set Header: `asila-api-key: sk-asila-...`

---

## Troubleshooting

### Database Connection Issues

**Error:** `asyncpg.exceptions.CannotConnectNowError`

**Solution:**
1. Verify PostgreSQL is running: `docker ps`
2. Ensure you are using `postgresql+asyncpg://` in your `DATABASE_URL`, not just `postgresql://` or `postgres://`.
3. Check the host name. If running locally, use `localhost`. If running via Docker Compose, use the service name (`postgres`).

### Background Jobs Not Processing

**Error:** Documents are stuck in "pending" status.

**Solution:**
1. Ensure the Arq worker is running. If using Docker, check `docker compose logs worker`.
2. Check if Redis is reachable: `redis-cli ping`
3. Look for errors in the worker output regarding missing API keys for the embedding models.

### Migration Issues

**Error:** `Relation "tenant" does not exist`

**Solution:**
Ensure you have run both the platform and the shared migrations:
```bash
cd backend
alembic -c alembic.platform.ini upgrade head
alembic -c alembic.shared.ini upgrade head
```

---

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, development process, and how to submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
