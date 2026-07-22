from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus


async def create_or_get_job(
    session: AsyncSession,
    *,
    organization_id: str,
    idempotency_key: str,
    document_id: str | None = None,
    operation: str = "embed",
    payload: dict | None = None,
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


async def start_job(job: IngestionJob, session: AsyncSession) -> None:
    if job.status != IngestionJobStatus.QUEUED:
        raise ValueError("Only queued jobs can start")
    job.status = IngestionJobStatus.PROCESSING
    job.attempts += 1
    job.started_at = datetime.now(timezone.utc)
    await session.flush()


async def complete_job(job: IngestionJob, session: AsyncSession) -> None:
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can complete")
    job.status = IngestionJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    await session.flush()


async def fail_job(job: IngestionJob, session: AsyncSession, error: str) -> None:
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can fail")
    job.status = IngestionJobStatus.FAILED
    job.last_error = error[:10000]
    await session.flush()


async def requeue_job(job: IngestionJob, session: AsyncSession, error: str) -> None:
    if job.status != IngestionJobStatus.PROCESSING:
        raise ValueError("Only processing jobs can be requeued")
    job.status = IngestionJobStatus.QUEUED
    job.last_error = error[:10000]
    job.available_at = datetime.now(timezone.utc)
    await session.flush()
