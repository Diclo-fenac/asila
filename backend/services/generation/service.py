from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam
from infra.llm.gemini import gemini_service
from domain.tenant.unanswered_queries.models import UnansweredQuery

class Citation(BaseModel):
    document_id: str
    document_title: str
    chunk_text: str
    page_number: Optional[int] = None
    score: float = 1.0

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

async def answer_query(db: AsyncSession, query: str, user_id: Optional[str] = None, conversation_id: Optional[str] = None) -> AnswerResponse:
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
    
    chunk_sql = text(
        "SELECT c.id, c.content, c.document_id, c.page_number, d.title "
        "FROM chunks c "
        "JOIN embeddings e ON c.id = e.chunk_id "
        "JOIN documents d ON c.document_id = d.id "
        "ORDER BY e.embedding <=> :vector LIMIT 10"
    )
    entity_sql = text("SELECT id, name, COALESCE(description, '') FROM entities ORDER BY embedding <=> :vector LIMIT 10")
    rel_sql = text("SELECT id::text, predicate FROM relationships ORDER BY embedding <=> :vector LIMIT 10")
    comm_sql = text("SELECT id, name, COALESCE(description, '') FROM communities ORDER BY embedding <=> :vector LIMIT 10")
    sum_sql = text(
        "SELECT ds.id, ds.summary, ds.document_id, d.title "
        "FROM document_summaries ds "
        "JOIN documents d ON ds.document_id = d.id "
        "ORDER BY ds.embedding <=> :vector LIMIT 10"
    )

    chunk_res = await db.execute(chunk_sql, {"vector": str_vector})
    ent_res = await db.execute(entity_sql, {"vector": str_vector})
    rel_res = await db.execute(rel_sql, {"vector": str_vector})
    comm_res = await db.execute(comm_sql, {"vector": str_vector})
    sum_res = await db.execute(sum_sql, {"vector": str_vector})

    chunk_cands = [
        {
            "id": str(r[0]),
            "type": "chunk",
            "content": r[1],
            "document_id": str(r[2]),
            "page_number": r[3],
            "document_title": r[4]
        }
        for r in chunk_res.all()
    ]
    ent_cands = [
        {
            "id": str(r[0]),
            "type": "entity",
            "content": f"{r[1]} - {r[2]}",
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Entity: {r[1]}"
        }
        for r in ent_res.all()
    ]
    rel_cands = [
        {
            "id": str(r[0]),
            "type": "relationship",
            "content": r[1],
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Relationship: {r[1]}"
        }
        for r in rel_res.all()
    ]
    comm_cands = [
        {
            "id": str(r[0]),
            "type": "community",
            "content": f"{r[1]} - {r[2]}",
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Community: {r[1]}"
        }
        for r in comm_res.all()
    ]
    sum_cands = [
        {
            "id": str(r[0]),
            "type": "summary",
            "content": r[1],
            "document_id": str(r[2]),
            "page_number": None,
            "document_title": f"Summary: {r[3]}"
        }
        for r in sum_res.all()
    ]

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
        ).bindparams(bindparam("eids", expanding=True))
        edge_res = await db.execute(edge_sql, {"eids": entity_ids})
        edges = edge_res.all()
        if edges:
            context_text += "Graph Relationships:\n"
            for row in edges:
                context_text += f"- {row[0]} {row[1]} {row[2]}\n"

    for f in fused[:15]:
        item = f["item"]
        score = f["score"]
        context_text += f"[{item['type'].upper()}]: {item['content']}\n\n"
        citations.append(
            Citation(
                document_id=item["document_id"],
                document_title=item["document_title"],
                chunk_text=item["content"],
                page_number=item.get("page_number"),
                score=score
            )
        )

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

    if not ("don't know" in english_answer.lower()):
        await _log_query(db, query, final_answer, user_id, conversation_id)

    return AnswerResponse(answer=final_answer, citations=citations, language=lang_code)

async def answer_query_stream(db: AsyncSession, query: str, user_id: Optional[str] = None, conversation_id: Optional[str] = None):
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

    # 3. Parallel ANN Searches
    chunk_sql = text(
        "SELECT c.id, c.content, c.document_id, c.page_number, d.title "
        "FROM chunks c "
        "JOIN embeddings e ON c.id = e.chunk_id "
        "JOIN documents d ON c.document_id = d.id "
        "ORDER BY e.embedding <=> :vector LIMIT 10"
    )
    entity_sql = text("SELECT id, name, COALESCE(description, '') FROM entities ORDER BY embedding <=> :vector LIMIT 10")
    rel_sql = text("SELECT id::text, predicate FROM relationships ORDER BY embedding <=> :vector LIMIT 10")
    comm_sql = text("SELECT id, name, COALESCE(description, '') FROM communities ORDER BY embedding <=> :vector LIMIT 10")
    sum_sql = text(
        "SELECT ds.id, ds.summary, ds.document_id, d.title "
        "FROM document_summaries ds "
        "JOIN documents d ON ds.document_id = d.id "
        "ORDER BY ds.embedding <=> :vector LIMIT 10"
    )

    chunk_res = await db.execute(chunk_sql, {"vector": str_vector})
    ent_res = await db.execute(entity_sql, {"vector": str_vector})
    rel_res = await db.execute(rel_sql, {"vector": str_vector})
    comm_res = await db.execute(comm_sql, {"vector": str_vector})
    sum_res = await db.execute(sum_sql, {"vector": str_vector})

    chunk_cands = [
        {
            "id": str(r[0]),
            "type": "chunk",
            "content": r[1],
            "document_id": str(r[2]),
            "page_number": r[3],
            "document_title": r[4]
        }
        for r in chunk_res.all()
    ]
    ent_cands = [
        {
            "id": str(r[0]),
            "type": "entity",
            "content": f"{r[1]} - {r[2]}",
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Entity: {r[1]}"
        }
        for r in ent_res.all()
    ]
    rel_cands = [
        {
            "id": str(r[0]),
            "type": "relationship",
            "content": r[1],
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Relationship: {r[1]}"
        }
        for r in rel_res.all()
    ]
    comm_cands = [
        {
            "id": str(r[0]),
            "type": "community",
            "content": f"{r[1]} - {r[2]}",
            "document_id": str(r[0]),
            "page_number": None,
            "document_title": f"Community: {r[1]}"
        }
        for r in comm_res.all()
    ]
    sum_cands = [
        {
            "id": str(r[0]),
            "type": "summary",
            "content": r[1],
            "document_id": str(r[2]),
            "page_number": None,
            "document_title": f"Summary: {r[3]}"
        }
        for r in sum_res.all()
    ]

    # 4. RRF Fusion
    fused = reciprocal_rank_fusion([chunk_cands, ent_cands, rel_cands, comm_cands, sum_cands])
    
    if not fused:
        await _log_unanswered(db, query, user_id)
        yield {"type": "chunk", "content": "I don't have any information to answer that."}
        yield {"type": "done", "citations": []}
        return

    top_items = [f["item"] for f in fused[:15]]
    
    # 5. Graph Traversal Expansion
    context_text = "Retrieved Context:\n"
    citations = []
    
    entity_ids = [item["id"] for item in top_items if item["type"] == "entity"]
    if entity_ids:
        edge_sql = text(
            "SELECT e1.name, r.predicate, e2.name "
            "FROM relationships r "
            "JOIN entities e1 ON r.source_id = e1.id "
            "JOIN entities e2 ON r.target_id = e2.id "
            "WHERE r.source_id IN :eids OR r.target_id IN :eids LIMIT 20"
        ).bindparams(bindparam("eids", expanding=True))
        edge_res = await db.execute(edge_sql, {"eids": entity_ids})
        edges = edge_res.all()
        if edges:
            context_text += "Graph Relationships:\n"
            for row in edges:
                context_text += f"- {row[0]} {row[1]} {row[2]}\n"

    for f in fused[:15]:
        item = f["item"]
        score = f["score"]
        context_text += f"[{item['type'].upper()}]: {item['content']}\n\n"
        citations.append(
            Citation(
                document_id=item["document_id"],
                document_title=item["document_title"],
                chunk_text=item["content"],
                page_number=item.get("page_number"),
                score=score
            )
        )

    # 6. Synthesis
    system_prompt = (
        "You are Asila, a precise assistant. Answer using ONLY the provided Context. "
        "Do not hallucinate."
    )
    if lang_code.lower() not in ["en", "english"]:
        system_prompt += f" Write your response in the language corresponding to code: '{lang_code}'."
        
    final_prompt = f"{system_prompt}\n\n{context_text}\n\nUser Question: {translated_query}"
    
    # 7. Stream response from Gemini
    full_answer = ""
    async for token in gemini_service.generate_response_stream(final_prompt):
        full_answer += token
        yield {"type": "chunk", "content": token}

    # 8. Unanswered Query Check
    if "don't know" in full_answer.lower() or "don't have" in full_answer.lower():
        await _log_unanswered(db, query, user_id)
    else:
        await _log_query(db, query, full_answer, user_id, conversation_id)

    # 9. Yield done event containing citations
    yield {"type": "done", "citations": [c.model_dump() for c in citations]}

async def _log_unanswered(db: AsyncSession, query: str, user_id: str = None):
    if user_id:
        from domain.tenant.users.models import User
        from sqlalchemy import select
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            user_id = None

    uq = UnansweredQuery(user_id=user_id, question=query)
    db.add(uq)
    await db.commit()

async def _log_query(db: AsyncSession, query: str, answer: str, user_id: Optional[str] = None, conversation_id: Optional[str] = None):
    if not user_id:
        return
        
    from domain.tenant.users.models import User
    from domain.tenant.queries.models import Query
    from sqlalchemy import select
    
    # Ensure user exists in the tenant database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user_exists = result.scalar_one_or_none()
    
    if not user_exists:
        new_user = User(id=user_id, name=user_id.split("@")[0])
        db.add(new_user)
        await db.flush()
        
    q = Query(user_id=user_id, conversation_id=conversation_id, question=query, answer=answer)
    db.add(q)
    await db.commit()
