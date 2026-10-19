"""
Ingestion retry fencing, stale recovery, lease ownership, and deletion lifecycle acceptance tests (MAY-111 / DOC-03).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from domain.app.documents.models import Document, DocumentStatus
from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from services.documents import delete_document_lifecycle, parse_and_persist_chunks
from services.ingestion_jobs import (
    MAX_INGESTION_ATTEMPTS,
    FencedExecutionError,
    cancel_job,
    complete_job,
    fail_job,
    requeue_job,
    start_job,
)
from workers.core import process_next_job


# ==============================================================================
# Invariant 1: Finite Retry Attempts and Backoff
# ==============================================================================

@pytest.mark.asyncio
async def test_finite_retry_attempts_and_backoff():
    """Job requeues with backoff when attempts < 5, but terminates when attempts reach cap."""
    session = MagicMock()
    session.flush = AsyncMock()

    # Attempt 1: requeue succeeds with backoff
    job = MagicMock(
        id="job_retry_1",
        status=IngestionJobStatus.PROCESSING,
        attempts=1,
        lease_id="lease_1",
    )
    requeued = await requeue_job(job, session, "PARSER_TIMEOUT", lease_id="lease_1")
    assert requeued is True
    assert job.status == IngestionJobStatus.QUEUED
    assert job.last_error == "PARSER_TIMEOUT"
    assert job.available_at > datetime.now(timezone.utc)
    assert job.lease_id is None

    # Attempt 5: exhausted job fails permanently with MAX_ATTEMPTS_EXCEEDED
    job.status = IngestionJobStatus.PROCESSING
    job.attempts = 5
    job.lease_id = "lease_5"
    requeued_5 = await requeue_job(job, session, "PARSER_TIMEOUT", lease_id="lease_5")
    assert requeued_5 is False
    assert job.status == IngestionJobStatus.FAILED
    assert job.last_error == "MAX_ATTEMPTS_EXCEEDED"
    assert job.completed_at is not None


# ==============================================================================
# Invariant 2: Lease Fencing on Completion and Failure
# ==============================================================================

@pytest.mark.asyncio
async def test_fenced_late_writes_rejected_on_superseded_lease():
    """A worker with an outdated or mismatched lease cannot complete or fail a job."""
    session = MagicMock()
    session.flush = AsyncMock()

    job = MagicMock(
        id="job_fenced_1",
        status=IngestionJobStatus.PROCESSING,
        lease_id="lease_worker_b",
    )

    # Worker A attempts to complete with its stale lease "lease_worker_a"
    with pytest.raises(FencedExecutionError):
        await complete_job(job, session, lease_id="lease_worker_a")

    # Worker A attempts to fail with stale lease
    with pytest.raises(FencedExecutionError):
        await fail_job(job, session, "FAILED", lease_id="lease_worker_a")

    # Worker A attempts to requeue with stale lease
    with pytest.raises(FencedExecutionError):
        await requeue_job(job, session, "FAILED", lease_id="lease_worker_a")

    # Worker B with matching lease completes successfully
    await complete_job(job, session, lease_id="lease_worker_b")
    assert job.status == IngestionJobStatus.COMPLETED


# ==============================================================================
# Invariant 3: Cancellation Fencing & Worker Termination
# ==============================================================================

@pytest.mark.asyncio
async def test_cancellation_fencing_prevents_completion():
    """Cancelling a job transitions it to CANCELLED and fences off any subsequent completion."""
    session = MagicMock()
    session.flush = AsyncMock()

    job = MagicMock(
        id="job_cancel_1",
        status=IngestionJobStatus.PROCESSING,
        lease_id="lease_cancel",
    )

    cancelled = await cancel_job(job, session, "USER_CANCELLED")
    assert cancelled is True
    assert job.status == IngestionJobStatus.CANCELLED
    assert job.last_error == "USER_CANCELLED"
    assert job.lease_id is None

    # Subsequent completion by worker is fenced off
    with pytest.raises(FencedExecutionError):
        await complete_job(job, session, lease_id="lease_cancel")


# ==============================================================================
# Invariant 4: Revocation During Processing Terminates Without Retry
# ==============================================================================

@pytest.mark.asyncio
async def test_revocation_during_processing_fails_cleanly(monkeypatch):
    """When permission or source is revoked/deleted during processing, job fails immediately without retry."""
    job = MagicMock(
        id="job_rev_1",
        status=IngestionJobStatus.PROCESSING,
        attempts=1,
        lease_id="lease_rev",
    )

    session = MagicMock()
    session.flush = AsyncMock()

    # When revoked, worker must not requeue regardless of attempts count
    await fail_job(job, session, "AUTHORIZATION_REVOKED", lease_id="lease_rev")
    assert job.status == IngestionJobStatus.FAILED
    assert job.last_error == "AUTHORIZATION_REVOKED"


# ==============================================================================
# Invariant 5: Idempotent Deletion Lifecycle & Immediate Tombstoning
# ==============================================================================

@pytest.mark.asyncio
async def test_delete_document_lifecycle_tombstones_and_cancels_jobs():
    """Document deletion immediately tombstones access, cancels active jobs, and purges storage."""
    session = MagicMock()
    document = MagicMock(id="doc_del_1", status=DocumentStatus.READY, repository_id="col_1")
    revisions = [MagicMock(id="rev_1", status="ready"), MagicMock(id="rev_2", status="quarantined")]
    jobs = [MagicMock(id="job_1", status=IngestionJobStatus.PROCESSING), MagicMock(id="job_2", status=IngestionJobStatus.QUEUED)]

    # Mock execute results
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = document

    rev_result = MagicMock()
    rev_result.all.return_value = revisions

    jobs_result = MagicMock()
    jobs_result.all.return_value = jobs

    session.execute = AsyncMock(side_effect=[doc_result, MagicMock()])
    session.scalars = AsyncMock(side_effect=[rev_result, jobs_result])
    session.flush = AsyncMock()

    with patch("infra.storage.local.storage_service.delete_document_storage") as mock_storage_del:
        summary = await delete_document_lifecycle(
            session,
            organization_id="org_test",
            document_id="doc_del_1",
        )

        assert summary["status"] == "deleted"
        assert summary["revisions_deleted"] == 2
        assert summary["cancelled_jobs"] == 2

        # Document tombstoned
        assert document.status == DocumentStatus.DELETED

        # Revisions tombstoned
        assert all(r.status == "deleted" for r in revisions)
        assert all(r.publication_status == "blocked" for r in revisions)

        # Active jobs cancelled
        assert all(j.status == IngestionJobStatus.CANCELLED for j in jobs)

        # Storage cleanup called
        mock_storage_del.assert_called_once_with(
            organization_id="org_test",
            collection_id="col_1",
            document_id="doc_del_1",
        )


# ==============================================================================
# Invariant 6: Logs Retain Zero Sentinel Document Content
# ==============================================================================

@pytest.mark.asyncio
async def test_logs_contain_zero_sentinel_content(caplog):
    """When parsing or ingestion fails, logs retain only safe codes and identifiers, never document text."""
    sentinel = "SUPER_SECRET_PAYLOAD_CONTENT_DO_NOT_LOG"
    doc = MagicMock(id="doc_secret", extracted_text=sentinel, status=DocumentStatus.READY)

    session = MagicMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = doc
    session.execute = AsyncMock(return_value=exec_result)
    session.flush = AsyncMock()

    with patch("httpx.AsyncClient.post", side_effect=ValueError(f"Unexpected token in: {sentinel}")), \
         caplog.at_level("DEBUG"):
        with pytest.raises(Exception):
            await parse_and_persist_chunks(session, "org_test", "doc_secret")

        # The log must NOT contain the sentinel text!
        assert sentinel not in caplog.text
        # But should contain safe identifiers and error type
        assert "doc_secret" in caplog.text
        assert "ValueError" in caplog.text


# ==============================================================================
# Invariant 7: Unscoped Worker Claim Fails Closed (RLS Boundary)
# ==============================================================================

@pytest.mark.asyncio
async def test_unscoped_worker_claim_fails_closed():
    """Worker process_next_job without dispatch_context=True fails closed immediately."""
    claimed = await process_next_job(dispatch_context=False)
    assert claimed is False
