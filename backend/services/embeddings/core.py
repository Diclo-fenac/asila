from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.chunks.models import Chunk
from domain.app.embeddings.models import Embedding
from domain.ports.ai import EmbeddingProvider


async def embed_document_chunks(
    session: AsyncSession,
    *,
    organization_id: str,
    document_id: str,
    provider: EmbeddingProvider,
) -> list[Embedding]:
    result = await session.execute(
        select(Chunk)
        .where(
            Chunk.organization_id == organization_id,
            Chunk.document_id == document_id,
        )
        .order_by(Chunk.ordinal.asc())
    )
    chunks = result.scalars().all()
    if not chunks:
        return []

    await session.execute(
        delete(Embedding).where(
            Embedding.organization_id == organization_id,
            Embedding.chunk_id.in_([chunk.id for chunk in chunks]),
        )
    )

    vectors = await provider.embed([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding provider returned an unexpected vector count")
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or not dimensions:
        raise RuntimeError("Embedding provider returned inconsistent dimensions")
    dimension = dimensions.pop()
    if dimension <= 0:
        raise RuntimeError("Embedding provider returned an empty vector")

    embeddings = []
    for chunk, vector in zip(chunks, vectors):
        embedding = Embedding(
            id=f"emb_{chunk.id}",
            organization_id=organization_id,
            chunk_id=chunk.id,
            collection_key=f"{provider.model}:{dimension}",
            provider=provider.__class__.__name__,
            model=provider.model,
            dimension=dimension,
            embedding=vector,
        )
        session.add(embedding)
        embeddings.append(embedding)
    await session.flush()
    return embeddings
