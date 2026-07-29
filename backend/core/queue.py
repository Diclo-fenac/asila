async def enqueue_ingestion_job(organization_id: str, job_id: str) -> None:
    """
    Publish a durable job reference.
    With Ponytail architecture (PostgreSQL polling via SKIP LOCKED),
    the worker loop automatically picks up jobs inserted in the database.
    This function is a no-op.
    """
    pass
