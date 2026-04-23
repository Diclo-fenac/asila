from typing import List, Dict, Any, Optional
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from domain.tenant.chunks.models import Chunk
from domain.tenant.embeddings.models import Embedding
from domain.tenant.documents.models import Document
from services.embeddings.service import generate_embedding
from pydantic import BaseModel

class ChunkContext(BaseModel):
    content: str
    document_id: str
    document_title: str
    page_number: Optional[int]
    score: float

async def retrieve_context(db: AsyncSession, query: str, limit: int = 5) -> List[ChunkContext]:
    """
    Hybrid Search: Combines Vector Search (Semantic) and Full-Text Search (Keywords).
    Uses Reciprocal Rank Fusion (RRF) logic simplified via SQL.
    """
    query_vector = await generate_embedding(query)
    
    # We use a CTE to get top results from both methods and then combine them
    # For simplicity in this implementation, we'll do a weighted combination in SQL
    
    sql = text("""
        WITH vector_search AS (
            SELECT 
                chunk_id, 
                1 - (embedding <=> :vector) as semantic_score
            FROM embeddings
            ORDER BY embedding <=> :vector
            LIMIT 20
        ),
        fts_search AS (
            SELECT 
                id as chunk_id, 
                ts_rank_cd(search_vector, plainto_tsquery('english', :query)) as keyword_score
            FROM chunks
            WHERE search_vector @@ plainto_tsquery('english', :query)
            LIMIT 20
        )
        SELECT 
            c.content, 
            c.document_id, 
            d.title as document_title,
            c.page_number,
            COALESCE(v.semantic_score, 0) + COALESCE(f.keyword_score, 0) * 2.0 as combined_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN vector_search v ON c.id = v.chunk_id
        LEFT JOIN fts_search f ON c.id = f.chunk_id
        WHERE v.chunk_id IS NOT NULL OR f.chunk_id IS NOT NULL
        ORDER BY combined_score DESC
        LIMIT :limit
    """)
    
    result = await db.execute(sql, {"vector": query_vector, "query": query, "limit": limit})
    
    return [
        ChunkContext(
            content=row[0],
            document_id=row[1],
            document_title=row[2],
            page_number=row[3],
            score=row[4]
        ) for row in result.all()
    ]
