from arq import create_pool

from core.config.settings import settings
from workers.core import redis_settings_from_url


async def enqueue_ingestion_job(organization_id: str, job_id: str) -> None:
    """Publish a durable job reference; content stays in PostgreSQL/storage."""

    redis = await create_pool(redis_settings_from_url(settings.REDIS_URL))
    try:
        await redis.enqueue_job(
            "process_ingestion_job",
            organization_id,
            job_id,
            _job_id=job_id,
        )
    finally:
        await redis.close()
