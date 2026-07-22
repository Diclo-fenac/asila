from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.app.ingestion_jobs.models import IngestionJobStatus
from services.ingestion_jobs.service import (
    complete_job,
    create_or_get_job,
    fail_job,
    requeue_job,
    start_job,
)


@pytest.mark.asyncio
async def test_create_or_get_job_is_idempotent():
    existing = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    job = await create_or_get_job(
        session,
        organization_id="org_1",
        idempotency_key="repo:main:abc",
    )

    assert job is existing
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_job_state_transitions_are_explicit():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    job = await create_or_get_job(
        session,
        organization_id="org_1",
        idempotency_key="file:abc",
    )
    assert job.status == IngestionJobStatus.QUEUED

    await start_job(job, session)
    assert job.status == IngestionJobStatus.PROCESSING
    await complete_job(job, session)
    assert job.status == IngestionJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_failed_job_records_error():
    job = MagicMock(status=IngestionJobStatus.PROCESSING, attempts=1)
    session = MagicMock()
    session.flush = AsyncMock()

    await fail_job(job, session, "parser failed")

    assert job.status == IngestionJobStatus.FAILED
    assert job.last_error == "parser failed"


@pytest.mark.asyncio
async def test_requeue_job_preserves_retryable_failure_state():
    job = MagicMock(status=IngestionJobStatus.PROCESSING, attempts=1)
    session = MagicMock()
    session.flush = AsyncMock()

    await requeue_job(job, session, "embedding provider unavailable")

    assert job.status == IngestionJobStatus.QUEUED
    assert job.last_error == "embedding provider unavailable"
