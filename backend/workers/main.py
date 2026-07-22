"""ARQ entry point for the current shared-schema worker."""

from workers.core import WorkerSettings, process_ingestion_job


async def process_document_task(ctx, organization_id: str, job_id: str, **_kwargs):
    """Compatibility wrapper for callers migrating from the retired worker API."""

    return await process_ingestion_job(ctx, organization_id, job_id)
