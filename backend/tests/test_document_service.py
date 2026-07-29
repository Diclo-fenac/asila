from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.app.documents.models import DocumentStatus
from services.documents import create_document, parse_and_persist_chunks


@pytest.mark.asyncio
async def test_create_document_adds_document_to_session():
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
    assert document.status == DocumentStatus.READY
    assert session.add.call_count == 1
    await session.flush()


@pytest.mark.asyncio
async def test_parse_and_persist_chunks_creates_chunk_entities():
    doc = MagicMock(id="doc_1", organization_id="org_1", extracted_text="Hello world section")
    result = MagicMock()
    result.scalar_one_or_none.return_value = doc
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.add = MagicMock()

    fake_docling_response = MagicMock()
    fake_docling_response.json.return_value = {
        "chunks": [
            {"text": "Chunk 1 text", "headings": ["Intro"], "page_numbers": [1], "num_tokens": 10},
            {"text": "Chunk 2 text", "headings": ["Details"], "page_numbers": [2], "num_tokens": 20},
        ]
    }

    with patch("services.documents.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post.return_value = fake_docling_response
        mock_client_cls.return_value.__aenter__.return_value = client

        await parse_and_persist_chunks(session, "org_1", "doc_1")

    assert session.add.call_count == 2
