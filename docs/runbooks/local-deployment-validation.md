# Runbook: Local Deployment & Stack Validation (MAY-112 / DOC-04)

This runbook guides Platform Operators through deploying, verifying, and validating the hardened Asila document service deployment using Docker Compose, least-privilege PostgreSQL roles, and isolated microservice sockets.

---

## 1. Architecture & Service Isolation Invariants

The deployment stack enforces strict multi-tenancy, least-privilege database roles, and process isolation:

1. **PostgreSQL 16 (`postgres`)**:
   - Pinned image `pgvector/pgvector:pg16`.
   - Host binding: `127.0.0.1:${POSTGRES_PORT:-5432}:5432` (never `0.0.0.0`).
   - Least-privilege roles bootstrapped on init:
     - `asila_migrator`: Schema ownership (`platform`, `app`), `NOBYPASSRLS`, used solely by the `migrate` service.
     - `asila_app`: DML table privileges (`SELECT, INSERT, UPDATE, DELETE`) and sequence usage; `NOBYPASSRLS` enforced across all tables (`FORCE ROW LEVEL SECURITY`).
   - Transactional claim routine `app.claim_next_ingestion_job` runs with fixed `search_path = app, pg_catalog, pg_temp` and `SECURITY DEFINER` to dispatch jobs under RLS.

2. **Database Migration (`migrate`)**:
   - Executes dual Alembic heads (`alembic.platform.ini` and `alembic.app.ini`) as `asila_migrator`.
   - Completes before `api` and `worker` start (`condition: service_completed_successfully`).

3. **API Service (`api`)**:
   - Runs as non-root user `asila` (UID 1000).
   - Localhost-only published port: `127.0.0.1:${ASILA_PORT:-8000}:8000`.
   - Volume mounts:
     - `/var/lib/asila/private`: Read-write volume for document upload and physical deletion lifecycle.
     - `/run/asila-scanner`: Read-only socket mount (`:ro`).
     - `/run/asila-parser`: Read-only socket mount (`:ro`).

4. **Worker Service (`worker`)**:
   - Runs as non-root user `asila` (UID 1000).
   - Reads storage volume strictly read-only (`/var/lib/asila/private:ro`).
   - Communicates with scanner and parser strictly via isolated read-only Unix sockets.
   - Enforces atomic attempt increments (capped at 5), exponential retry backoff, lease fencing (`FencedExecutionError`), and crash recovery.

5. **Document Scanner (`document_scanner`)**:
   - Pinned ClamAV image digest.
   - `network_mode: none`, `read_only: true`, `cap_drop: [ALL]`.
   - Listens on `/run/asila-scanner/clamd.sock`.

6. **Document Parser (`document_parser`)**:
   - Pinned Docling image digest with offline model cache.
   - `network_mode: none`, `read_only: true`, `cap_drop: [ALL]`.
   - Listens on `/run/asila-parser/parser.sock`.

---

## 2. Pinned Deployment Procedure

### Step 1: Environment Configuration
Copy `.env.example` and supply strong randomized passwords. For local test runs that coexist with host services, set non-conflicting ports:
```bash
cp .env.example .env
export POSTGRES_PORT=5433
export ASILA_PORT=8001
export POSTGRES_PASSWORD=your_secure_admin_password
export ASILA_DB_APP_PASSWORD=your_secure_app_password
export ASILA_DB_MIGRATOR_PASSWORD=your_secure_migrator_password
export ASILA_SETUP_TOKEN=$(openssl rand -hex 16)
export ASILA_MASTER_KEY=$(openssl rand -hex 32)
```

### Step 2: Launch Stack
Boot the infrastructure and application services:
```bash
docker compose -f deployments/docker-compose.yml up -d postgres migrate api worker
```

Verify service health:
```bash
docker compose -f deployments/docker-compose.yml ps
```

---

## 3. Automated Service Acceptance Verification

Execute the MAY-112 acceptance suite to verify the end-to-end security and isolation invariants:
```bash
DATABASE_URL="postgresql+asyncpg://asila_app:${ASILA_DB_APP_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/asila_platform" \
ASILA_TEST_ADMIN_URL="postgresql+asyncpg://asila_admin:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/asila_platform" \
POSTGRES_PASSWORD="${ASILA_DB_APP_PASSWORD}" \
pytest tests/test_service_acceptance.py -v
```

**Verified Invariants**:
- `test_least_privilege_database_roles_and_rls`: Proves `asila_migrator` and `asila_app` are `NOBYPASSRLS` and all `app` tables have `FORCE RLS` enabled.
- `test_isolated_document_upload_across_formats_without_ai_provider`: Proves PDF, DOCX, TXT, and Markdown upload, SHA-256 validation, and `0o700` storage directory isolation without external AI calls.
- `test_multitenancy_and_collection_boundary_enforcement`: Proves cross-tenant requests and ungranted collections reject with 403/404 and RLS `42501`.
- `test_midflight_revocation_and_deletion_stops_execution`: Proves revoked collection grants or deleted documents fail running jobs immediately without retrying (`AUTHORIZATION_REVOKED`, `SOURCE_DELETED`).
- `test_queue_resilience_lease_fencing_and_deletion_lifecycle`: Proves 5-attempt retry exhaustion (`MAX_ATTEMPTS_EXCEEDED`), lease fencing (`FencedExecutionError`), and idempotent document deletion cleanup.
- `test_privacy_and_logging_hygiene`: Proves zero document sentinel content or raw exception bodies leak into logs.
- `test_deployment_specifications_and_cloud_blocker_invariants`: Verifies compose isolation, `127.0.0.1` bindings, and non-root user enforcement.

---

## 4. Remaining Cloud & Production Blockers

Local volume storage and process isolation are verified. However, enterprise cloud production requirements remain explicit blockers pending specialist infrastructure delivery:
1. **Cloud KMS & Storage-at-Rest Encryption**: Local volume storage enforces filesystem `0o700` permissions; managed cloud S3/GCS bucket-level encryption (KMS customer-managed keys) and envelope encryption remain unverified.
2. **Private VPC Endpoints**: Cloud storage access must route over private VPC endpoints without public Internet transit.
3. **Regional Multi-Zone Redundancy**: Multi-AZ failover and data residency guarantees remain external infrastructure dependencies.
4. **Immutable Backup Retention & Disaster Recovery**: Cold storage retention and point-in-time recovery runbooks remain uncertified for production.
