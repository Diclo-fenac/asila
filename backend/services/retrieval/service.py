from dataclasses import asdict, dataclass
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document, DocumentStatus
from domain.app.embeddings.models import Embedding
from domain.ports.ai import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk_id: str
    document_id: str
    title: str
    source_uri: str
    content: str
    page_number: int | None
    score: float

    def as_dict(self) -> dict:
        return asdict(self)


def validate_query(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query.strip())
    if not normalized:
        raise ValueError("Search query is required")
    return normalized


def normalize_search_limit(limit: int | None) -> int:
    if limit is None:
        return 10
    return min(max(limit, 1), 50)


async def keyword_search(
    session: AsyncSession,
    query: str,
    *,
    limit: int | None = None,
    repository_id: str | None = None,
) -> list[SearchResult]:
    query = validate_query(query)
    limit = normalize_search_limit(limit)
    ts_query = func.plainto_tsquery("simple", query)
    rank = func.ts_rank_cd(Chunk.search_vector, ts_query).label("rank")
    statement = (
        select(Chunk, Document, rank)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.search_vector.op("@@")(ts_query),
            Document.status != DocumentStatus.DELETED,
        )
        .order_by(rank.desc(), Chunk.ordinal.asc())
        .limit(limit)
    )
    if repository_id:
        statement = statement.where(Document.repository_id == repository_id)
    result = await session.execute(statement)
    return [
        SearchResult(
            chunk_id=chunk.id,
            document_id=document.id,
            title=document.title,
            source_uri=document.source_uri,
            content=chunk.content,
            page_number=chunk.page_number,
            score=float(score),
        )
        for chunk, document, score in result.all()
    ]


async def semantic_search(
    session: AsyncSession,
    query: str,
    *,
    provider: EmbeddingProvider,
    limit: int | None = None,
    repository_id: str | None = None,
) -> list[SearchResult]:
    query = validate_query(query)
    limit = normalize_search_limit(limit)
    vectors = await provider.embed([query])
    if len(vectors) != 1 or not vectors[0]:
        raise RuntimeError("Embedding provider returned an invalid query vector")
    query_vector = vectors[0]
    collection_key = f"{provider.model}:{len(query_vector)}"
    distance = Embedding.embedding.cosine_distance(query_vector).label("distance")
    statement = (
        select(Chunk, Document, distance)
        .join(Document, Document.id == Chunk.document_id)
        .join(Embedding, Embedding.chunk_id == Chunk.id)
        .where(
            Embedding.collection_key == collection_key,
            Document.status != DocumentStatus.DELETED,
        )
        .order_by(distance.asc(), Chunk.ordinal.asc())
        .limit(limit)
    )
    if repository_id:
        statement = statement.where(Document.repository_id == repository_id)
    result = await session.execute(statement)
    return [
        SearchResult(
            chunk_id=chunk.id,
            document_id=document.id,
            title=document.title,
            source_uri=document.source_uri,
            content=chunk.content,
            page_number=chunk.page_number,
            score=max(0.0, 1.0 - float(distance_value)),
        )
        for chunk, document, distance_value in result.all()
    ]


def reciprocal_rank_fusion(
    ranked_lists: list[list[SearchResult | dict]], *, k: int = 60
) -> list[SearchResult | dict]:
    fused: dict[str, tuple[float, SearchResult | dict]] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            identifier = item.chunk_id if isinstance(item, SearchResult) else item["chunk_id"]
            score, existing = fused.get(identifier, (0.0, item))
            fused[identifier] = (score + 1.0 / (k + rank + 1), existing)
    return [item for _, item in sorted(fused.values(), key=lambda pair: pair[0], reverse=True)]


async def hybrid_search(
    session: AsyncSession,
    query: str,
    *,
    provider: EmbeddingProvider,
    limit: int | None = None,
    repository_id: str | None = None,
) -> list[SearchResult]:
    lexical = await keyword_search(session, query, limit=limit, repository_id=repository_id)
    semantic = await semantic_search(
        session, query, provider=provider, limit=limit, repository_id=repository_id
    )
    return [item for item in reciprocal_rank_fusion([lexical, semantic]) if isinstance(item, SearchResult)][:normalize_search_limit(limit)]
