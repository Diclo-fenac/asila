from dataclasses import asdict, dataclass
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document, DocumentStatus
from domain.app.embeddings.models import Embedding
from domain.ports.ai import EmbeddingProvider
from core.resilience import circuit_breaker
from core.exceptions.resilience import ServiceUnavailableError


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
    ts_query = func.plainto_tsquery("english", query)
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
    @circuit_breaker(name="ollama", failure_threshold=3, recovery_timeout=60)
    async def _embed():
        return await provider.embed([query])
        
    vectors = await _embed()
    if len(vectors) != 1 or not vectors[0]:
        raise RuntimeError("Embedding provider returned an invalid query vector")
    query_vector = vectors[0]
    collection_key = f"{provider.model}:{len(query_vector)}"
    distance = Embedding.embedding.max_inner_product(query_vector).label("distance")
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
            score=max(0.0, -float(distance_value)),
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
    query_str = validate_query(query)
    search_limit = normalize_search_limit(limit)
    k = 60

    ts_query = func.plainto_tsquery("english", query_str)
    lexical_rank = func.ts_rank_cd(Chunk.search_vector, ts_query).label("rank")
    lexical_stmt = (
        select(
            Chunk.id.label("chunk_id"),
            func.row_number().over(order_by=[lexical_rank.desc(), Chunk.ordinal.asc()]).label("rank_pos")
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.search_vector.op("@@")(ts_query),
            Document.status != DocumentStatus.DELETED,
        )
    )
    if repository_id:
        lexical_stmt = lexical_stmt.where(Document.repository_id == repository_id)
    lexical_cte = lexical_stmt.limit(search_limit).cte("lexical")

    try:
        @circuit_breaker(name="ollama", failure_threshold=3, recovery_timeout=60)
        async def _embed():
            return await provider.embed([query_str])
            
        vectors = await _embed()
        if len(vectors) != 1 or not vectors[0]:
            raise RuntimeError("Embedding provider returned an invalid query vector")
        query_vector = vectors[0]
    except (ServiceUnavailableError, Exception) as e:
        logging.getLogger(__name__).warning(f"Semantic search degraded: {e}")
        return await keyword_search(session, query, limit=limit, repository_id=repository_id)
        
    collection_key = f"{provider.model}:{len(query_vector)}"
    distance = Embedding.embedding.max_inner_product(query_vector).label("distance")
    
    semantic_stmt = (
        select(
            Chunk.id.label("chunk_id"),
            func.row_number().over(order_by=[distance.asc(), Chunk.ordinal.asc()]).label("rank_pos")
        )
        .join(Document, Document.id == Chunk.document_id)
        .join(Embedding, Embedding.chunk_id == Chunk.id)
        .where(
            Embedding.collection_key == collection_key,
            Document.status != DocumentStatus.DELETED,
        )
    )
    if repository_id:
        semantic_stmt = semantic_stmt.where(Document.repository_id == repository_id)
    semantic_cte = semantic_stmt.limit(search_limit).cte("semantic")

    coalesced_chunk_id = func.coalesce(lexical_cte.c.chunk_id, semantic_cte.c.chunk_id).label("chunk_id")
    rrf_score = (
        func.coalesce(1.0 / (k + lexical_cte.c.rank_pos), 0.0) +
        func.coalesce(1.0 / (k + semantic_cte.c.rank_pos), 0.0)
    ).label("score")

    statement = (
        select(Chunk, Document, rrf_score)
        .select_from(
            lexical_cte.join(
                semantic_cte,
                lexical_cte.c.chunk_id == semantic_cte.c.chunk_id,
                full=True
            )
        )
        .join(Chunk, Chunk.id == coalesced_chunk_id)
        .join(Document, Document.id == Chunk.document_id)
        .order_by(rrf_score.desc(), Chunk.ordinal.asc())
        .limit(search_limit)
    )

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
