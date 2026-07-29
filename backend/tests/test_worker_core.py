import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from domain.app.ingestion_jobs.models import IngestionJobStatus
from workers.core import process_next_job

def _job():
    return MagicMock(
        id="job_1",
        organization_id="org_1",
        document_id="doc_1",
        operation="embed",
        status=IngestionJobStatus.PROCESSING,
        attempts=0,
    )

@pytest.mark.asyncio
async def test_worker_embeds_and_completes_job():
    job = _job()
    result = MagicMock()
    result.fetchone.return_value = ("job_1", "org_1")
    result.scalar_one.return_value = job
    
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
        patch("workers.core.parse_and_persist_chunks", new=AsyncMock(return_value=None)),
        patch("workers.core.embed_document_chunks", new=AsyncMock(return_value=[])),
    ):
        processed = await process_next_job()

    assert processed is True
    assert job.status == IngestionJobStatus.COMPLETED
