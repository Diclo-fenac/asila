"""Unscoped queue dispatch must not bypass runtime collection RLS."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_collection_authorization import collection_context as collection_context
from workers.core import process_next_job


@pytest.mark.asyncio
async def test_worker_does_not_claim_without_authorized_dispatch_context(
    collection_context,
):
    c = collection_context
    job_id = f"job_{uuid4().hex}"
    async with c["admin"].begin() as db:
        await db.execute(
            text("""INSERT INTO app.ingestion_jobs
            (id,organization_id,document_id,idempotency_key,operation,payload_json,status,attempts)
            VALUES (:id,:org,:doc,:id,'embed','{}','queued',0)"""),
            {"id": job_id, "org": c["org"], "doc": c["documents"][0]},
        )
    assert await process_next_job() is False
    async with c["admin"].connect() as db:
        state = (
            await db.execute(
                text(
                    "SELECT status,attempts FROM app.ingestion_jobs WHERE id=:id"
                ),
                {"id": job_id},
            )
        ).one()
    assert state == ("queued", 0)
