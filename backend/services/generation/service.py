from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from infra.llm.gemini import gemini_service
from domain.tenant.unanswered_queries.models import UnansweredQuery

class Citation(BaseModel):
    id: str
    type: str

class AnswerResponse(BaseModel):
    answer: str
    citations: List[Citation]
    language: str

def reciprocal_rank_fusion(candidate_lists: list[list], k=60):
    scores = {}
    # candidate is expected to be a dict: {"id": str, "type": str, "content": str}
    for candidates in candidate_lists:
        for rank, item in enumerate(candidates):
            item_id = item["id"]
            if item_id not in scores:
                scores[item_id] = {"item": item, "score": 0.0}
            scores[item_id]["score"] += 1.0 / (k + rank)
    
    return sorted(scores.values(), key=lambda x: x["score"], reverse=True)

async def answer_query(db: AsyncSession, query: str, user_id: Optional[str] = None) -> AnswerResponse:
    # 1. Translate Query
    lang_info_prompt = f"Detect the language of this query and translate it to English. Return format: 'LANG_CODE | TRANSLATED_TEXT'. Query: {query}"
    lang_res = await gemini_service.generate_response(lang_info_prompt)
    try:
        lang_code, translated_query = [s.strip() for s in lang_res.split('|', 1)]
    except:
        lang_code, translated_query = "en", query

    # 2. Generate Query Embedding
    query_vector = await gemini_service.generate_embedding(translated_query)
    str_vector = str(query_vector)

    # 3. Parallel ANN Searches (Chunk, Entity, Relationship, Community, DocumentSummary)
    # Using execute since asyncpg handles concurrent execution under the hood or we can await them sequentially (fast enough)
    
    chunk_sql = text("SELECT c.id, c.content FROM chunks c JOIN embeddings e ON c.id = e.chunk_id ORDER BY e.embedding <=> :vector LIMIT 10")
    entity_sql = text("SELECT id, name || ' - ' || COALESCE(description, '') FROM entities ORDER BY embedding <=> :vector LIMIT 10")
    rel_sql = text("SELECT id::text, predicate FROM relationships ORDER BY embedding <=> :vector LIMIT 10")
    comm_sql = text("SELECT id, name || ' - ' || COALESCE(description, '') FROM communities ORDER BY embedding <=> :vector LIMIT 10")
    sum_sql = text("SELECT id, summary FROM document_summaries ORDER BY embedding <=> :vector LIMIT 10")

    chunk_res = await db.execute(chunk_sql, {"vector": str_vector})
    ent_res = await db.execute(entity_sql, {"vector": str_vector})
    rel_res = await db.execute(rel_sql, {"vector": str_vector})
    comm_res = await db.execute(comm_sql, {"vector": str_vector})
    sum_res = await db.execute(sum_sql, {"vector": str_vector})

    chunk_cands = [{"id": r[0], "type": "chunk", "content": r[1]} for r in chunk_res.all()]
    ent_cands = [{"id": r[0], "type": "entity", "content": r[1]} for r in ent_res.all()]
    rel_cands = [{"id": r[0], "type": "relationship", "content": r[1]} for r in rel_res.all()]
    comm_cands = [{"id": r[0], "type": "community", "content": r[1]} for r in comm_res.all()]
    sum_cands = [{"id": r[0], "type": "summary", "content": r[1]} for r in sum_res.all()]

    # 4. RRF Fusion
    fused = reciprocal_rank_fusion([chunk_cands, ent_cands, rel_cands, comm_cands, sum_cands])
    
    if not fused:
        await _log_unanswered(db, query, user_id)
        return AnswerResponse(answer="I don't have any information to answer that.", citations=[], language=lang_code)

    top_items = [f["item"] for f in fused[:15]]
    
    # 5. Graph Traversal Expansion for Entities/Communities
    context_text = "Retrieved Context:\n"
    citations = []
    
    entity_ids = [item["id"] for item in top_items if item["type"] == "entity"]
    if entity_ids:
        # Traverse 1 hop edges
        edge_sql = text(
            "SELECT e1.name, r.predicate, e2.name "
            "FROM relationships r "
            "JOIN entities e1 ON r.source_id = e1.id "
            "JOIN entities e2 ON r.target_id = e2.id "
            "WHERE r.source_id IN :eids OR r.target_id IN :eids LIMIT 20"
        )
        edge_res = await db.execute(edge_sql, {"eids": tuple(entity_ids)})
        edges = edge_res.all()
        if edges:
            context_text += "Graph Relationships:\n"
            for row in edges:
                context_text += f"- {row[0]} {row[1]} {row[2]}\n"

    for item in top_items:
        context_text += f"[{item['type'].upper()}]: {item['content']}\n\n"
        citations.append(Citation(id=item["id"], type=item["type"]))

    # 6. Synthesis
    system_prompt = (
        "You are Asila, a precise assistant. Answer using ONLY the provided Context. "
        "Do not hallucinate."
    )
    final_prompt = f"{system_prompt}\n\n{context_text}\n\nUser Question: {translated_query}"
    english_answer = await gemini_service.generate_response(final_prompt)

    if "don't know" in english_answer.lower():
        await _log_unanswered(db, query, user_id)

    final_answer = english_answer
    if lang_code.lower() != "en" and lang_code.lower() != "english":
        final_answer = await gemini_service.generate_response(f"Translate this text to {lang_code}: {english_answer}")

    return AnswerResponse(answer=final_answer, citations=citations, language=lang_code)

async def _log_unanswered(db: AsyncSession, query: str, user_id: str = None):
    uq = UnansweredQuery(user_id=user_id, question=query)
    db.add(uq)
    await db.commit()
