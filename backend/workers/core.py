import asyncio
from sqlalchemy import select, text
from core.database.app_session import AppSessionLocal, set_transaction_organization
from core.organization.context import organization_scope
from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from services.ai_factory import build_organization_embedding_provider
from services.embeddings import embed_document_chunks
from services.documents import parse_and_persist_chunks
from services.ingestion_jobs import complete_job, fail_job, requeue_job, start_job

MAX_INGESTION_ATTEMPTS = 5

async def process_next_job() -> bool:
    """Poll the database for the next queued job using SKIP LOCKED."""
    async with AppSessionLocal() as session:
        async with session.begin():
            # Raw SQL for cross-tenant queue popping (needs to run as platform admin or similar)
            # Actually, IngestionJob is a tenant table. We can't query across tenants without RLS bypass.
            # We can run as bypass (since worker needs to see all tenants)
            result = await session.execute(
                text("""
                    UPDATE app.ingestion_jobs
                    SET status = 'processing', updated_at = now()
                    WHERE id = (
                        SELECT id FROM app.ingestion_jobs
                        WHERE status = 'queued'
                        ORDER BY created_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING id, organization_id;
                """)
            )
            row = result.fetchone()
            if not row:
                return False

            job_id, organization_id = row[0], row[1]
    
    # We have a job, process it in tenant context
    try:
        provider = await build_organization_embedding_provider(organization_id)
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_organization(session, organization_id)
                    # Fetch job
                    result = await session.execute(
                        select(IngestionJob).where(IngestionJob.id == job_id)
                    )
                    job = result.scalar_one()
                    
                    await parse_and_persist_chunks(session, organization_id, job.document_id)
                    await embed_document_chunks(session, organization_id=organization_id, document_id=job.document_id, provider=provider)
                    await complete_job(job, session)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_organization(session, organization_id)
                    result = await session.execute(select(IngestionJob).where(IngestionJob.id == job_id))
                    job = result.scalar_one()
                    if job.attempts < MAX_INGESTION_ATTEMPTS:
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
        except Exception as e:
            print(f"Worker loop error: {e}")
            await asyncio.sleep(5.0)

if __name__ == "__main__":
    asyncio.run(worker_loop())
