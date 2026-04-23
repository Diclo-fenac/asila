# Asila Phase 2: Tenant-Level Schema Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete tenant-level database schema to support the RAG pipeline, citizen interactions, and geo-targeted broadcasts.

**Architecture:** A comprehensive schema residing in each isolated Tenant DB, utilizing `pgvector` for AI memory and `PostGIS` for geo-spatial targeting.

**Tech Stack:** SQLAlchemy 2.0, pgvector, PostGIS, Alembic.

---

## Chunk 1: RAG & Document Models

### Task 1: Document & Chunk Models

**Files:**
- Modify: `domain/tenant/documents/models.py`
- Create: `domain/tenant/chunks/models.py`

- [ ] **Step 1: Implement `Document` model in `domain/tenant/documents/models.py`**

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON
from datetime import datetime
from core.database.base import TenantBase

class Document(TenantBase):
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Create `domain/tenant/chunks/models.py`**

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey
from core.database.base import TenantBase

class Chunk(TenantBase):
    __tablename__ = "chunks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(String)
    page_number: Mapped[int | None] = mapped_column(Integer)
```

- [ ] **Step 3: Commit**

```bash
git add domain/tenant/documents/models.py domain/tenant/chunks/models.py
git commit -m "feat(tenant): add document and chunk models"
```

### Task 2: Embedding Model (pgvector)

**Files:**
- Create: `domain/tenant/embeddings/models.py`

- [ ] **Step 1: Create `domain/tenant/embeddings/models.py`**

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey
from pgvector.sqlalchemy import Vector
from core.database.base import TenantBase

class Embedding(TenantBase):
    __tablename__ = "embeddings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("chunks.id"))
    embedding: Mapped[Vector] = mapped_column(Vector(768)) # Gemini 768-dim
```

- [ ] **Step 2: Commit**

```bash
git add domain/tenant/embeddings/models.py
git commit -m "feat(tenant): add embedding model with pgvector"
```

## Chunk 2: User & Interaction Models

### Task 3: User & Query Models (PostGIS)

**Files:**
- Create: `domain/tenant/users/models.py`
- Create: `domain/tenant/queries/models.py`

- [x] **Step 1: Create `domain/tenant/users/models.py`**

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from core.database.base import TenantBase

class User(TenantBase):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # WhatsApp ID
    name: Mapped[str | None] = mapped_column(String)
    location: Mapped[any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    ward_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [x] **Step 2: Create `domain/tenant/queries/models.py`**

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, ForeignKey
from datetime import datetime
from core.database.base import TenantBase

class Query(TenantBase):
    __tablename__ = "queries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [x] **Step 3: Commit**

```bash
git add domain/tenant/users/models.py domain/tenant/queries/models.py
git commit -m "feat(tenant): add user and query models with PostGIS support"
```

## Chunk 3: Migrations & Template Update

### Task 4: Tenant Initial Migration

**Files:**
- Modify: `migrations/tenant/env.py`
- Create: `migrations/tenant/versions/...`

- [ ] **Step 1: Update `migrations/tenant/env.py` imports**
Ensure all tenant models are imported so Alembic "sees" them.

- [ ] **Step 2: Create initial tenant migration**

Run: `uv run alembic -c alembic.tenant.ini revision --autogenerate -m "initial tenant schema"`

- [ ] **Step 3: Commit**

```bash
git add migrations/tenant/versions/
git commit -m "feat(tenant): generate initial tenant schema migration"
```

### Task 5: Update Bootstrap to Apply Migrations

**Files:**
- Modify: `scripts/bootstrap_tenant.py`

- [ ] **Step 1: Update `scripts/bootstrap_tenant.py`**
Add logic to run the Alembic migration against the `asila_schema_template` after extensions are created.

- [ ] **Step 2: Run bootstrap to verify**

Run: `python -m scripts.bootstrap_tenant`
Expected: Success, and `asila_schema_template` contains all 9 tables.

- [ ] **Step 3: Commit**

```bash
git add scripts/bootstrap_tenant.py
git commit -m "chore(tenant): update bootstrap to apply schema migrations"
```
