import asyncio
from sqlalchemy import select, text
from core.database.app_session import (
    AppSessionLocal,
    set_transaction_organization,
    set_transaction_principal,
)
from core.organization.context import organization_scope
from domain.app.ingestion_jobs.models import IngestionJob
from services.ai_factory import build_organization_embedding_provider
from services.embeddings import embed_document_chunks
from services.documents import parse_and_persist_chunks
from services.ingestion_jobs import complete_job, fail_job, requeue_job
from services.collections import require_collection
from services.job_authorization import job_principal
from domain.app.documents.models import Document, DocumentStatus
from fastapi import HTTPException

MAX_INGESTION_ATTEMPTS = 5


async def process_next_job() -> bool:
    """Poll the database for the next queued job using SKIP LOCKED."""
    async with AppSessionLocal() as session:
        async with session.begin():
            # Runtime RLS denies unscoped dispatch. DOC-03 must provide bounded,
            # organization-scoped claiming; never deploy this worker with BYPASSRLS.
            result = await session.execute(
                text("""
                    UPDATE app.ingestion_jobs
                    SET status = 'processing', updated_at = now(), attempts = attempts + 1, started_at = now()
                    WHERE id = (
                        SELECT id FROM app.ingestion_jobs
                        WHERE status = 'queued'
                        ORDER BY created_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING id, organization_id, document_id, payload_json;
                """)
            )
            row = result.fetchone()
            if not row:
                return False

            job_id, organization_id, document_id, payload = (
                row[0],
                row[1],
                row[2],
                row[3],
            )

    # We have a job, process it in tenant context
    try:
        principal = await job_principal(organization_id, payload)
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_principal(session, principal)
                    document = await session.scalar(
                        select(Document).where(
                            Document.id == document_id,
                            Document.status != DocumentStatus.DELETED,
                        )
                    )
                    if document is None:
                        raise HTTPException(403, "AUTHORIZATION_REVOKED")
                    await require_collection(
                        session, principal, document.repository_id, "extract"
                    )
                    job = await session.scalar(
                        select(IngestionJob).where(IngestionJob.id == job_id)
                    )
                    if job is None:
                        raise HTTPException(403, "AUTHORIZATION_REVOKED")
                    provider = await build_organization_embedding_provider(
                        organization_id
                    )

                    await parse_and_persist_chunks(
                        session, organization_id, job.document_id
                    )
                    await embed_document_chunks(
                        session,
                        organization_id=organization_id,
                        document_id=job.document_id,
                        provider=provider,
                    )
                    current_principal = await job_principal(
                        organization_id, payload
                    )
                    await set_transaction_principal(session, current_principal)
                    await require_collection(
                        session,
                        current_principal,
                        document.repository_id,
                        "extract",
                    )
                    await complete_job(job, session)
    except Exception as exc:
        revoked = isinstance(exc, HTTPException) and exc.status_code == 403
        error = "AUTHORIZATION_REVOKED" if revoked else "PROCESSING_FAILED"
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_organization(session, organization_id)
                    await session.execute(
                        text(
                            "SELECT set_config('app.job_dispatcher', 'true', true)"
                        )
                    )
                    result = await session.execute(
                        select(IngestionJob).where(IngestionJob.id == job_id)
                    )
                    job = result.scalar_one()
                    if not revoked and job.attempts < MAX_INGESTION_ATTEMPTS:
                        await requeue_job(job, session, error)
                    else:
                        await fail_job(job, session, error)

    return True


async def worker_loop():
    print("🚀 Ponytail Worker started: polling PostgreSQL directly.")
    while True:
        try:
            processed = await process_next_job()
            if not processed:
                await asyncio.sleep(1.0)
        except Exception:
            print("Worker loop failed; retrying after delay")
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    asyncio.run(worker_loop())
