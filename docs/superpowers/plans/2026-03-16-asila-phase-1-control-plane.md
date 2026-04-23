# Asila Phase 1: Control Plane Implementation Plan (DDD Structured)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the foundation of the Asila platform using a Domain-Driven Design (DDD) structure, including the central FastAPI server, the Platform (Meta) DB, and Auth0 integration.

**Architecture:** A Modular Monolith (FastAPI) with a "Database-per-Tenant" storage model. Uses two separate Alembic instances: one for the Platform Meta-DB and one for the Tenant-level schema.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, PostgreSQL (PostGIS + pgvector), Redis, Auth0, Poetry, Docker Compose.

---

## Chunk 1: Foundation & Infrastructure

### Task 1: Project Initialization & Directory Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env`
- Create: `apps/api/main.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[tool.poetry]
name = "asila"
version = "0.1.0"
description = "Verified Information Hub for Governments"
authors = ["Gemini CLI <bot@asila.gov>"]
readme = "README.md"
package-mode = false

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = "^0.27.1"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.27"}
asyncpg = "^0.29.0"
pydantic-settings = "^2.2.1"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
httpx = "^0.27.0"
alembic = "^1.13.1"
redis = {extras = ["hiredis"], version = "^5.0.1"}

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.2"
pytest-asyncio = "^0.23.5"
httpx = "^0.27.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry-core.masonry.api"
```

- [ ] **Step 2: Initialize directory structure**

```bash
mkdir -p apps/api/routes apps/webhook apps/worker
mkdir -p core/config core/database core/tenant core/security core/logging core/exceptions
mkdir -p domain/platform/tenants domain/tenant/documents domain/tenant/chunks domain/tenant/queries domain/tenant/users
mkdir -p services/ingestion services/enrichment services/embeddings services/retrieval services/generation services/notifications services/analytics
mkdir -p infra/postgres infra/redis infra/storage infra/twilio infra/llm
mkdir -p migrations/platform migrations/tenant
mkdir -p workers deployments/docker deployments/kubernetes scripts
```

- [ ] **Step 3: Create initial `.env` file**

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/asila_platform
REDIS_URL=redis://localhost:6379/0
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_AUDIENCE=https://api.asila.gov
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

- [ ] **Step 4: Create a basic `apps/api/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Asila API")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env apps/api/main.py
git commit -m "feat: initialize project with DDD directory structure"
```

### Task 2: Infrastructure with Docker Compose (PostGIS + pgvector)

**Files:**
- Create: `deployments/docker/docker-compose.yml`

- [ ] **Step 1: Create `deployments/docker/docker-compose.yml`**

```yaml
version: '3.8'

services:
  db:
    image: postgis/postgis:15-3.3 # Includes PostGIS
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: asila_platform
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: >
      sh -c "docker-entrypoint.sh postgres -c shared_preload_libraries=pgvector"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 2: Run `docker-compose up -d`**

Run: `docker-compose -f deployments/docker/docker-compose.yml up -d`
Expected: DB and Redis containers running.

- [ ] **Step 3: Commit**

```bash
git add deployments/docker/docker-compose.yml
git commit -m "chore: setup infrastructure with PostGIS support"
```

## Chunk 2: Dual-Layer Database & Migrations

### Task 3: Base Models & Platforms Session

**Files:**
- Create: `core/config/settings.py`
- Create: `core/database/base.py`
- Create: `core/database/platform_session.py`

- [ ] **Step 1: Create `core/config/settings.py`**

- [ ] **Step 2: Create `core/database/base.py` (Dual Bases)**

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class PlatformBase(Base):
    pass

class TenantBase(Base):
    pass
```

- [ ] **Step 3: Create `core/database/platform_session.py`**

- [ ] **Step 4: Commit**

```bash
git add core/config/settings.py core/database/base.py core/database/platform_session.py
git commit -m "feat: setup configuration and platform db session"
```

### Task 4: Platform & Tenant Migrations

**Files:**
- Create: `domain/platform/tenants/models.py`
- Create: `domain/tenant/documents/models.py`
- Create: `alembic.platform.ini`
- Create: `alembic.tenant.ini`

- [ ] **Step 1: Initialize Platform Alembic**

Run: `poetry run alembic -c alembic.platform.ini init migrations/platform`

- [ ] **Step 2: Initialize Tenant Alembic**

Run: `poetry run alembic -c alembic.tenant.ini init migrations/tenant`

- [ ] **Step 3: Configure `migrations/platform/env.py` to target `PlatformBase`**

- [ ] **Step 4: Configure `migrations/tenant/env.py` to target `TenantBase`**

- [ ] **Step 5: Create initial Tenant Table in `domain/platform/tenants/models.py`**

- [ ] **Step 6: Commit**

```bash
git add migrations/ alembic.*.ini
git commit -m "feat: setup dual-layer migrations for platform and tenants"
```

## Chunk 3: Security & Tenancy Core

### Task 5: Auth & Tenancy Resolver

**Files:**
- Create: `core/security/auth.py`
- Create: `core/tenant/resolver.py`
- Create: `core/database/tenant_session.py`
- Modify: `apps/api/main.py`

- [ ] **Step 1: Create `core/security/auth.py`**

- [ ] **Step 2: Create `core/tenant/resolver.py` (Cached Resolver)**

- [ ] **Step 3: Create `core/database/tenant_session.py` (Engine Pool)**

- [ ] **Step 4: Update `apps/api/main.py` with Tenancy Middleware**

- [ ] **Step 5: Commit**

```bash
git add core/security/auth.py core/tenant/resolver.py core/database/tenant_session.py apps/api/main.py
git commit -m "feat: implement security layer and tenancy resolver"
```

## Chunk 4: Tenant Factory & Bootstrap

### Task 6: Tenant Factory & Template Seeding

**Files:**
- Create: `domain/platform/tenants/service.py`
- Create: `scripts/bootstrap_tenant.py`

- [ ] **Step 1: Create `domain/platform/tenants/service.py` (Tenant Factory)**

```python
from sqlalchemy import text
from core.database.platform_session import PlatformSessionLocal, engine as platform_engine
from domain.platform.tenants.models import Tenant

async def create_tenant(tenant_id: str, tenant_name: str):
    db_name = f"asila_tenant_{tenant_id}"
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    
    async with platform_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(f"CREATE DATABASE {db_name} TEMPLATE asila_schema_template"))
    
    async with PlatformSessionLocal() as session:
        tenant = Tenant(id=tenant_id, name=tenant_name, db_connection_string=db_url)
        session.add(tenant)
        await session.commit()
    return db_url
```

- [ ] **Step 2: Create `scripts/bootstrap_tenant.py` (Template Seeder)**

```python
import asyncio
from sqlalchemy import text
from core.database.platform_session import engine as platform_engine
from domain.platform.tenants.service import create_tenant

async def bootstrap():
    async with platform_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP DATABASE IF EXISTS asila_schema_template"))
        await conn.execute(text("CREATE DATABASE asila_schema_template"))
        
        # Enable Extensions in Template
        # Note: Must be superuser or have permission
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Apply Tenant Migrations to Template
        # TODO: Run 'alembic -c alembic.tenant.ini upgrade head' against template URL
    
    await create_tenant("org_test_123", "Test Council")
    print("Bootstrap success!")

if __name__ == "__main__":
    asyncio.run(bootstrap())
```

- [ ] **Step 3: Run bootstrap**

Run: `python -m scripts.bootstrap_tenant`
Expected: "Bootstrap success!"

- [ ] **Step 4: Commit**

```bash
git add domain/platform/tenants/service.py scripts/bootstrap_tenant.py
git commit -m "feat: add tenant factory and bootstrap script with extension support"
```
