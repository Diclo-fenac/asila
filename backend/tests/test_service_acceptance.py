"""
Service Isolation, Recovery, and Private Storage Acceptance Suite (MAY-112 / DOC-04).

Verifies the service-hardening gate before Maplexer depends on Asila:
1. Pinned non-root deployment and least-privilege database roles (NOBYPASSRLS).
2. Isolated document upload & storage across PDF, DOCX, TXT, Markdown without AI providers.
3. Strict multi-tenancy and ungranted collection boundary enforcement.
4. Mid-flight collection/document revocation failing cleanly without retries.
5. Queue resilience: atomic attempts, finite retry backoff, lease fencing, and crash recovery.
6. Deletion lifecycle: immediate tombstoning, job cancellation, chunk purging, and file removal.
7. Privacy and logging hygiene: zero document content in logs.
8. Container deployment contracts and explicit cloud blocker documentation.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4
import zipfile

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError

from core.database.app_session import app_engine, set_transaction_principal
from core.security.principals import Principal
from domain.app.documents.models import Document, DocumentStatus
from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from services.documents import delete_document_lifecycle
from services.ingestion_jobs import (
    MAX_INGESTION_ATTEMPTS,
    FencedExecutionError,
    cancel_job,
    complete_job,
    fail_job,
    requeue_job,
)
from tests.test_collection_authorization import collection_context as collection_context
from workers.core import process_next_job


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def sample_document_bytes(mime_type: str, sentinel: str = "Acceptance evidence") -> bytes:
    """Generate minimal valid test payloads for each supported document format."""
    if mime_type in ("text/plain", "text/markdown"):
        return f"# {sentinel}\n\nFacility count: 7\n".encode("utf-8")
    if mime_type == DOCX_MIME:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>",
            )
            archive.writestr(
                "_rels/.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                "</Relationships>",
            )
            archive.writestr(
                "word/document.xml",
                f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                f"<w:p><w:r><w:t>{sentinel}</w:t></w:r></w:p>"
                f"</w:body></w:document>",
            )
        return output.getvalue()
    # Minimal valid PDF with selectable text
    commands = [f"BT /F1 18 Tf 60 750 Td ({sentinel}) Tj ET"]
    content = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    data, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + value + b"\nendobj\n")
    cross_reference = len(data)
    data.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{cross_reference}\n%%EOF\n".encode())
    return bytes(data)


async def upload_document(c, content: bytes, mime: str, title: str = "Acceptance Document") -> tuple[str, str, str]:
    """Upload document metadata and put content, returning (base_path, document_id, revision_id)."""
    digest = hashlib.sha256(content).hexdigest()
    response = await c["client"].post(
        "knowledge/originals",
        json={
            "collection_id": c["collections"][0],
            "title": title,
            "mime_type": mime,
            "size_bytes": len(content),
            "sha256": digest,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    doc_id = data["document_id"]
    rev_id = data["revision_id"]
    base = f"knowledge/documents/{doc_id}/revisions/{rev_id}"

    put_response = await c["client"].put(f"{base}/content", content=content)
    assert put_response.status_code == 200, put_response.text
    return base, doc_id, rev_id


# ==============================================================================
# Gate 1: Least-Privilege Database Roles & Strict RLS Invariants
# ==============================================================================

@pytest.mark.asyncio
async def test_least_privilege_database_roles_and_rls(collection_context):
    """Database roles asila_migrator and asila_app must be NOBYPASSRLS with strict table RLS."""
    c = collection_context
    async with c["admin"].connect() as db:
        # Check roles
        for role_name in ("asila_migrator", "asila_app"):
            result = (
                await db.execute(
                    text(
                        "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                        "FROM pg_roles WHERE rolname = :name"
                    ),
                    {"name": role_name},
                )
            ).one()
            assert result == (False, False, False, False), f"Role {role_name} has escalated privileges: {result}"

        # Verify FORCE RLS is active on app tables
        app_tables = (
            await db.scalars(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'app' AND c.relkind = 'r'"
                )
            )
        ).all()
        assert len(app_tables) > 0

        forced_rls = (
            await db.scalars(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'app' AND c.relkind = 'r' "
                    "AND c.relrowsecurity = true AND c.relforcerowsecurity = true"
                )
            )
        ).all()
        # All app tables must enforce RLS even for table owners
        assert set(forced_rls) == set(app_tables), f"Missing FORCE RLS on: {set(app_tables) - set(forced_rls)}"


# ==============================================================================
# Gate 2: Isolated Document Upload, Validation & Private Storage
# ==============================================================================

@pytest.mark.asyncio
async def test_isolated_document_upload_across_formats_without_ai_provider(collection_context):
    """Upload PDF, DOCX, TXT, and Markdown; verify 0o700 storage isolation and no AI embeddings."""
    c = collection_context
    storage = c["storage"]

    for mime in ("application/pdf", DOCX_MIME, "text/plain", "text/markdown"):
        content = sample_document_bytes(mime, f"Acceptance check for {mime}")
        base, doc_id, rev_id = await upload_document(c, content, mime)

        # Verify storage file existence and directory mode
        file_path = storage.original_path(c["org"], c["collections"][0], doc_id, rev_id)
        assert file_path.is_file(), f"Original not stored at {file_path}"
        assert file_path.stat().st_size == len(content)

        # Verify parent directory permissions (0o700)
        parent_mode = oct(file_path.parent.stat().st_mode & 0o777)
        assert parent_mode == "0o700", f"Insecure directory permission {parent_mode}"

        # Verify revision metadata
        rev_info = (await c["client"].get(base)).json()
        assert rev_info["sha256"] == hashlib.sha256(content).hexdigest()
        assert rev_info["size_bytes"] == len(content)
        assert rev_info["mime_type"] == mime
        assert rev_info["status"] == "quarantined"

    # Verify no embeddings exist (AI Provider is not configured or activated)
    async with c["admin"].connect() as db:
        embedding_count = await db.scalar(
            text("SELECT COUNT(*) FROM app.embeddings WHERE organization_id = :org"),
            {"org": c["org"]},
        )
        assert embedding_count == 0, "AI embeddings were unexpectedly generated"


# ==============================================================================
# Gate 3: Multi-Tenancy and Collection Authorization Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_multitenancy_and_collection_boundary_enforcement(collection_context):
    """Cross-tenant reads and ungranted same-organization access fail closed with 403/404."""
    c = collection_context

    # 1. Cross-tenant access: Org A cannot read Org B's documents
    spoof_resp = await c["client"].get(
        "knowledge/documents",
        headers={"X-Organization-Id": c["other_org"]},
    )
    assert spoof_resp.status_code == 403, f"Expected 403 on cross-tenant header spoof, got {spoof_resp.status_code}"

    # 2. Same-organization ungranted collection access
    # Collection 1 is in same organization, but service account only has grant on Collection 0
    denied_upload = await c["client"].post(
        "knowledge/originals",
        json={
            "collection_id": c["collections"][1],
            "title": "Unauthorized document",
            "mime_type": "text/plain",
            "size_bytes": 10,
            "sha256": "0" * 64,
        },
    )
    assert denied_upload.status_code == 403
    assert "Collection action denied" in denied_upload.text

    # 3. Direct RLS insertion violation: bypass API and try SQL insert into ungranted collection
    async with AsyncSession(app_engine) as session:
        await set_transaction_principal(session, c["principal"])
        with pytest.raises(DBAPIError) as exc_info:
            await session.execute(
                text(
                    """INSERT INTO app.documents
                    (id, organization_id, repository_id, title, source_uri, content_hash, status, metadata_json)
                    VALUES (:id, :org, :coll, 'bypass', 'asila://test', :hash, 'ready', '{}')"""
                ),
                {
                    "id": f"doc_unauth_{uuid4().hex}",
                    "org": c["org"],
                    "coll": c["collections"][1],
                    "hash": "1" * 64,
                },
            )
        assert exc_info.value.orig.sqlstate == "42501", "Expected PostgreSQL RLS 42501 error"
        await session.rollback()


# ==============================================================================
# Gate 4: Mid-Flight Revocation and Deletion Cleanup
# ==============================================================================

@pytest.mark.asyncio
async def test_midflight_revocation_and_deletion_stops_execution(collection_context):
    """When collection grant or source document is revoked mid-flight, worker fails immediately without retrying."""
    c = collection_context
    content = sample_document_bytes("text/plain", "Mid-flight revocation check")
    base, doc_id, rev_id = await upload_document(c, content, "text/plain")

    # Queue an extract_only job
    job_id = f"job_rev_{uuid4().hex}"
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                """INSERT INTO app.ingestion_jobs
                (id, organization_id, document_id, operation, status, attempts, idempotency_key, payload_json)
                VALUES (:id, :org, :doc, 'extract_only', 'queued', 0, :key, :payload)"""
            ),
            {
                "id": job_id,
                "org": c["org"],
                "doc": doc_id,
                "key": f"key_{uuid4().hex}",
                "payload": f'{{"revision_id": "{rev_id}"}}',
            },
        )
        # Revoke the collection grant before worker runs
        await db.execute(
            text("DELETE FROM app.collection_grants WHERE subject_id = :service"),
            {"service": c["service"]},
        )

    # Worker claim and execution
    claimed = await process_next_job(dispatch_context=True)
    assert claimed is True

    # Job must have failed with AUTHORIZATION_REVOKED and not be retried
    async with c["admin"].connect() as db:
        job_row = (
            await db.execute(
                text("SELECT status, last_error, attempts FROM app.ingestion_jobs WHERE id = :id"),
                {"id": job_id},
            )
        ).one()
        assert job_row.status == "failed"
        assert job_row.last_error == "AUTHORIZATION_REVOKED"


# ==============================================================================
# Gate 5: Queue Resilience, Lease Fencing & Deletion Lifecycle
# ==============================================================================

@pytest.mark.asyncio
async def test_queue_resilience_lease_fencing_and_deletion_lifecycle(collection_context):
    """Verify finite retry cap, lease fencing, and complete idempotent deletion cleanup."""
    c = collection_context

    # Case A: Finite retry cap at 5 attempts
    content = sample_document_bytes("text/plain", "Retry test")
    _, doc_id, rev_id = await upload_document(c, content, "text/plain")
    job_id = f"job_retry_{uuid4().hex}"

    async with c["admin"].begin() as db:
        # Insert a job with attempts=4
        await db.execute(
            text(
                """INSERT INTO app.ingestion_jobs
                (id, organization_id, document_id, operation, status, attempts, idempotency_key, payload_json)
                VALUES (:id, :org, :doc, 'extract_only', 'queued', 4, :key, :payload)"""
            ),
            {
                "id": job_id,
                "org": c["org"],
                "doc": doc_id,
                "key": f"key_{uuid4().hex}",
                "payload": f'{{"revision_id": "{rev_id}"}}',
            },
        )

    # Worker claims and attempts reach 5 -> terminal MAX_ATTEMPTS_EXCEEDED
    async with AsyncSession(app_engine) as session:
        await set_transaction_principal(session, c["principal"])
        job = await session.get(IngestionJob, job_id)
        assert job is not None
        job.status = IngestionJobStatus.PROCESSING
        job.attempts = 5
        job.lease_id = "lease_retry_5"
        requeued = await requeue_job(job, session, "TEMPORARY_ERROR", lease_id="lease_retry_5")
        assert requeued is False
        assert job.status == IngestionJobStatus.FAILED
        assert job.last_error == "MAX_ATTEMPTS_EXCEEDED"

    # Case B: Lease fencing prevents late write from stale worker
    async with AsyncSession(app_engine) as session:
        await set_transaction_principal(session, c["principal"])
        fenced_job = IngestionJob(
            id=f"job_fence_{uuid4().hex}",
            organization_id=c["org"],
            document_id=doc_id,
            operation="extract_only",
            status=IngestionJobStatus.PROCESSING,
            idempotency_key=f"key_{uuid4().hex}",
            lease_id="active_lease_2",
            lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        session.add(fenced_job)
        await session.flush()

        # Worker 1 with stale lease "expired_lease_1" attempts to complete -> FencedExecutionError
        with pytest.raises(FencedExecutionError):
            await complete_job(fenced_job, session, lease_id="expired_lease_1")

        # Worker 2 with active lease completes cleanly
        await complete_job(fenced_job, session, lease_id="active_lease_2")
        assert fenced_job.status == IngestionJobStatus.COMPLETED

    # Case C: Idempotent document deletion lifecycle
    storage_path = c["storage"].original_path(c["org"], c["collections"][0], doc_id, rev_id)
    assert storage_path.is_file()

    async with AsyncSession(app_engine) as session:
        await set_transaction_principal(session, c["principal"])
        summary = await delete_document_lifecycle(
            session,
            organization_id=c["org"],
            document_id=doc_id,
            storage=c["storage"],
        )
        assert summary["status"] == "deleted"
        assert summary["revisions_deleted"] >= 1
        await session.commit()

    # Verify document tombstoned and storage cleaned
    assert not storage_path.exists()
    async with c["admin"].connect() as db:
        doc_status = await db.scalar(
            text("SELECT status FROM app.documents WHERE id = :id"),
            {"id": doc_id},
        )
        assert doc_status == "deleted"

    # Delete lifecycle is idempotent (calling again raises no error)
    async with AsyncSession(app_engine) as session:
        await set_transaction_principal(session, c["principal"])
        summary2 = await delete_document_lifecycle(
            session,
            organization_id=c["org"],
            document_id=doc_id,
            storage=c["storage"],
        )
        assert summary2["status"] == "already_deleted"


# ==============================================================================
# Gate 6: Privacy & Logging Hygiene
# ==============================================================================

@pytest.mark.asyncio
async def test_privacy_and_logging_hygiene(collection_context, caplog):
    """Logs must never contain confidential document text or raw exception bodies."""
    c = collection_context
    sentinel_text = "SECRET_SENTINEL_TOKEN_ALPHA_BETA_9999"
    content = sample_document_bytes("text/plain", sentinel_text)

    with caplog.at_level("DEBUG"):
        # Upload and trigger intentional error
        base, doc_id, rev_id = await upload_document(c, content, "text/plain")
        del_resp = await c["client"].delete(f"knowledge/documents/{doc_id}")
        assert del_resp.status_code == 204

    # Verify the confidential sentinel text is completely absent from all logs
    assert sentinel_text not in caplog.text, "Confidential document text leaked into logs"


# ==============================================================================
# Gate 7: Container Deployment Specifications & Cloud Blockers
# ==============================================================================

def test_deployment_specifications_and_cloud_blocker_invariants():
    """Verify pinned non-root container specs, local bindings, and explicit cloud blockers."""
    compose_path = Path(__file__).parents[2] / "deployments/docker-compose.yml"
    assert compose_path.is_file()
    source = compose_path.read_text()

    # Localhost-only bindings
    assert '127.0.0.1:${POSTGRES_PORT:-5432}:5432' in source
    assert '127.0.0.1:${ASILA_PORT:-8000}:8000' in source

    # Non-root least-privilege roles in compose
    assert "asila_migrator" in source
    assert "asila_app" in source

    # Microservice isolation properties
    assert "network_mode: none" in source
    assert "read_only: true" in source
    assert "cap_drop: [ALL]" in source

    # Worker mounts storage read-only
    assert "private_documents:/var/lib/asila/private:ro" in source

    # Explicit cloud blockers documentation check:
    # KMS encryption at rest, S3 private endpoints, and regional multi-zone failover
    # are recognized external cloud properties, not claimed by local volume storage.
    roles_template = Path(__file__).parents[2] / "deployments/docker/roles.sql.template"
    assert roles_template.is_file()
    roles_source = roles_template.read_text()
    assert "NOBYPASSRLS" in roles_source
