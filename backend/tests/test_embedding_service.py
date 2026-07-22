from unittest.mock import AsyncMock, MagicMock

import pytest

from services.embeddings.core import embed_document_chunks


class FakeProvider:
    model = "test-embedding"

    async def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


@pytest.mark.asyncio
async def test_embed_document_chunks_persists_provider_metadata():
    chunk_one = MagicMock(id="chunk_1", content="one")
    chunk_two = MagicMock(id="chunk_2", content="two")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [chunk_one, chunk_two]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    embeddings = await embed_document_chunks(
        session,
        organization_id="org_1",
        document_id="doc_1",
        provider=FakeProvider(),
    )

    assert len(embeddings) == 2
    assert all(item.dimension == 2 for item in embeddings)
    assert all(item.collection_key == "test-embedding:2" for item in embeddings)
    assert session.add.call_count == 2

