import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.app.ingestion_jobs.models import IngestionJobStatus
from workers.core import process_ingestion_job


def _job(status=IngestionJobStatus.QUEUED, attempts=0):
    return MagicMock(
        id="job_1",
        organization_id="org_1",
        document_id="doc_1",
        operation="embed",
        status=status,
        attempts=attempts,
    )


@pytest.mark.asyncio
async def test_worker_embeds_and_completes_job():
    job = _job()
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("workers.core.AppSessionLocal", session_factory),
        patch("workers.core.build_organization_embedding_provider", new=AsyncMock(return_value=MagicMock())),
        patch("workers.core.embed_document_chunks", new=AsyncMock(return_value=[])),
    ):
        await process_ingestion_job({"job_try": 1}, "org_1", "job_1")

    assert job.status == IngestionJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_worker_retries_provider_failures_with_backoff():
    job = _job(attempts=1)
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    from arq import Retry

    with (
        patch("workers.core.AppSessionLocal", session_factory),
        patch("workers.core.build_organization_embedding_provider", new=AsyncMock(side_effect=RuntimeError("offline"))),
    ):
        with pytest.raises(Retry) as exc_info:
            await process_ingestion_job({"job_try": 1}, "org_1", "job_1")

    assert job.status == IngestionJobStatus.QUEUED
    assert exc_info.value.defer_score == 5000


@pytest.mark.asyncio
async def test_worker_does_not_swallow_cancellation():
    job = _job()
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("workers.core.AppSessionLocal", session_factory),
        patch("workers.core.build_organization_embedding_provider", new=AsyncMock(return_value=MagicMock())),
        patch("workers.core.embed_document_chunks", new=AsyncMock(side_effect=asyncio.CancelledError)),
    ):
        with pytest.raises(asyncio.CancelledError):
            await process_ingestion_job({"job_try": 1}, "org_1", "job_1")
