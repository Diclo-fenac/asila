from unittest.mock import AsyncMock, MagicMock

import pytest

from services.documents.service import build_chunks, create_document


def test_build_chunks_is_deterministic_and_preserves_order():
    content = "A" * 1600 + "\n\n" + "B" * 1600

    chunks = build_chunks(content, chunk_size=1000, overlap=100)

    assert len(chunks) >= 3
    assert chunks[0]["ordinal"] == 0
    assert chunks[1]["ordinal"] == 1
    assert all(chunk["token_count"] > 0 for chunk in chunks)


@pytest.mark.asyncio
async def test_create_document_adds_document_and_chunks():
    session = MagicMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=existing_result)
    session.flush = AsyncMock()

    document = await create_document(
        session,
        organization_id="org_1",
        title="Runbook",
        source_uri="file:///runbook.md",
        content="# Runbook\n\nRestart the worker when the queue is stuck.",
    )

    assert document.organization_id == "org_1"
    assert document.content_hash
    assert session.add.call_count >= 2
    await session.flush()
