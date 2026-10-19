from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from core.security.principals import Principal

MAX_INGESTION_ATTEMPTS = 5


class FencedExecutionError(Exception):
    """Raised when an operation is attempted on an expired, cancelled, or superseded job lease."""
    pass


async def create_or_get_job(
    session: AsyncSession,
    *,
    organization_id: str,
    idempotency_key: str,
    document_id: str | None = None,
    operation: str = "embed",
    payload: dict | None = None,
    principal: Principal | None = None,
) -> IngestionJob:
    if not organization_id or not idempotency_key.strip():
        raise ValueError("Organization and idempotency key are required")
    result = await session.execute(
        select(IngestionJob).where(
            IngestionJob.organization_id == organization_id,
            IngestionJob.idempotency_key == idempotency_key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    payload = {key: value for key, value in (payload or {}).items() if key != "_authorization"}
    if principal is not None:
        if principal.organization_id != organization_id:
            raise ValueError("Job principal organization mismatch")
        payload["_authorization"] = {
            "credential_id": principal.credential_id,
            "user_id": principal.user_id,
            "service_account_id": principal.service_account_id,
        }
    job = IngestionJob(
        id=f"job_{uuid4().hex}",
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        document_id=document_id,
        operation=operation,
        payload_json=payload or {},
        status=IngestionJobStatus.QUEUED,
        attempts=0,
        available_at=datetime.now(timezone.utc),
    )
    session.add(job)
    await session.flush()
    return job


async def start_job(
    job: IngestionJob,
    session: AsyncSession,
    *,
    worker_id: str | None = None,
    lease_id: str | None = None,
    lease_seconds: int = 300,
) -> None:
    if job.status != IngestionJobStatus.QUEUED:
        raise ValueError("Only queued jobs can start")
    job.status = IngestionJobStatus.PROCESSING
    job.attempts += 1
    job.started_at = datetime.now(timezone.utc)
    if worker_id or lease_id:
        job.worker_id = worker_id
        job.lease_id = lease_id or f"lease_{uuid4().hex}"
        job.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
    await session.flush()


async def complete_job(
    job: IngestionJob,
    session: AsyncSession,
    *,
    lease_id: str | None = None,
) -> None:
    if job.status == IngestionJobStatus.CANCELLED:
        raise FencedExecutionError("Job was cancelled")
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can complete")
    if lease_id is not None and job.lease_id and job.lease_id != lease_id:
        raise FencedExecutionError("Job lease expired or superseded")
    job.status = IngestionJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    job.lease_id = None
    job.lease_expires_at = None
    job.worker_id = None
    await session.flush()


async def fail_job(
    job: IngestionJob,
    session: AsyncSession,
    error: str,
    *,
    lease_id: str | None = None,
) -> None:
    if job.status == IngestionJobStatus.CANCELLED:
        raise FencedExecutionError("Job was cancelled")
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can fail")
    if lease_id is not None and job.lease_id and job.lease_id != lease_id:
        raise FencedExecutionError("Job lease expired or superseded")
    job.status = IngestionJobStatus.FAILED
    job.last_error = error[:10000]
    job.completed_at = datetime.now(timezone.utc)
    job.lease_id = None
    job.lease_expires_at = None
    job.worker_id = None
    await session.flush()


async def requeue_job(
    job: IngestionJob,
    session: AsyncSession,
    error: str,
    *,
    lease_id: str | None = None,
) -> bool:
    if job.status == IngestionJobStatus.CANCELLED:
        raise FencedExecutionError("Job was cancelled")
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can be requeued")
    if lease_id is not None and job.lease_id and job.lease_id != lease_id:
        raise FencedExecutionError("Job lease expired or superseded")

    if job.attempts >= MAX_INGESTION_ATTEMPTS:
        await fail_job(job, session, "MAX_ATTEMPTS_EXCEEDED", lease_id=lease_id)
        return False

    delay_seconds = min(300, (2 ** job.attempts) * 5)
    job.status = IngestionJobStatus.QUEUED
    job.last_error = error[:10000]
    job.available_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    job.lease_id = None
    job.lease_expires_at = None
    job.worker_id = None
    await session.flush()
    return True


async def cancel_job(
    job: IngestionJob,
    session: AsyncSession,
    reason: str = "CANCELLED",
) -> bool:
    if job.status in (IngestionJobStatus.QUEUED, IngestionJobStatus.PROCESSING):
        job.status = IngestionJobStatus.CANCELLED
        job.last_error = reason[:10000]
        job.completed_at = datetime.now(timezone.utc)
        job.lease_id = None
        job.lease_expires_at = None
        job.worker_id = None
        await session.flush()
        return True
    return False
