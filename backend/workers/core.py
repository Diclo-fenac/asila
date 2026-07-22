import asyncio
import urllib.parse

from arq import Retry
from arq.connections import RedisSettings
from sqlalchemy import select

from core.config.settings import settings
from core.database.app_session import AppSessionLocal, set_transaction_organization
from core.organization.context import organization_scope
from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from services.ai.factory import build_organization_embedding_provider
from services.embeddings.core import embed_document_chunks
from services.ingestion_jobs.service import (
    complete_job,
    fail_job,
    requeue_job,
    start_job,
)


MAX_INGESTION_ATTEMPTS = 5


def redis_settings_from_url(redis_url: str) -> RedisSettings:
    parsed = urllib.parse.urlparse(redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


async def _start_job(organization_id: str, job_id: str) -> IngestionJob | None:
    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(organization_id):
                await set_transaction_organization(session, organization_id)
                result = await session.execute(
                    select(IngestionJob)
                    .where(
                        IngestionJob.id == job_id,
                        IngestionJob.organization_id == organization_id,
                    )
                    .with_for_update(skip_locked=True)
                )
                job = result.scalar_one_or_none()
                if job is None or job.status != IngestionJobStatus.QUEUED:
                    return None
                await start_job(job, session)
                return job


async def _finish_job(organization_id: str, job_id: str) -> None:
    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(organization_id):
                await set_transaction_organization(session, organization_id)
                result = await session.execute(
                    select(IngestionJob).where(
                        IngestionJob.id == job_id,
                        IngestionJob.organization_id == organization_id,
                    )
                )
                job = result.scalar_one_or_none()
                if job is not None and job.status == IngestionJobStatus.PROCESSING:
                    await complete_job(job, session)


async def _record_failure(
    organization_id: str,
    job_id: str,
    error: str,
    *,
    retryable: bool,
) -> None:
    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(organization_id):
                await set_transaction_organization(session, organization_id)
                result = await session.execute(
                    select(IngestionJob).where(
                        IngestionJob.id == job_id,
                        IngestionJob.organization_id == organization_id,
                    )
                )
                job = result.scalar_one_or_none()
                if job is None or job.status != IngestionJobStatus.PROCESSING:
                    return
                if retryable and job.attempts < MAX_INGESTION_ATTEMPTS:
                    await requeue_job(job, session, error)
                else:
                    await fail_job(job, session, error)


async def process_ingestion_job(ctx: dict, organization_id: str, job_id: str) -> None:
    """Process one organization-scoped ingestion job with durable state transitions."""

    job = await _start_job(organization_id, job_id)
    if job is None:
        return
    try:
        if job.operation != "embed" or not job.document_id:
            raise ValueError("Unsupported ingestion job or missing document reference")
        provider = await build_organization_embedding_provider(organization_id)
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_organization(session, organization_id)
                    await embed_document_chunks(
                        session,
                        organization_id=organization_id,
                        document_id=job.document_id,
                        provider=provider,
                    )
        await _finish_job(organization_id, job_id)
    except asyncio.CancelledError:
        await _record_failure(
            organization_id,
            job_id,
            "Job cancelled by worker shutdown",
            retryable=True,
        )
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        await _record_failure(organization_id, job_id, error, retryable=True)
        if job.attempts < MAX_INGESTION_ATTEMPTS:
            job_try = int(ctx.get("job_try", job.attempts))
            raise Retry(defer=5 * (2 ** max(job_try - 1, 0))) from exc


class WorkerSettings:
    functions = [process_ingestion_job]
    max_jobs = 10
    job_timeout = 900
    allow_abort_jobs = True
    redis_settings = redis_settings_from_url(settings.REDIS_URL)
