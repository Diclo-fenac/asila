from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from infra.llm.gemini import gemini_service
from services.retrieval.service import retrieve_context, ChunkContext
from domain.tenant.unanswered_queries.models import UnansweredQuery

class Citation(BaseModel):
    document_id: str
    document_title: str
    page_number: Optional[int]

class AnswerResponse(BaseModel):
    answer: str
    citations: List[Citation]
    language: str

async def answer_query(db: AsyncSession, query: str, user_id: Optional[str] = None) -> AnswerResponse:
    """
    Advanced RAG Workflow:
    1. Detect Language & Translate to English.
    2. Retrieve Context via Hybrid Search.
    3. Generate Grounded Answer with Citations.
    4. Handle Knowledge Gaps (Unanswered Queries).
    5. Translate back if necessary.
    """
    # 1. Language Detection & Initial Translation
    # We ask Gemini to detect and translate if not English
    lang_info_prompt = f"Detect the language of this query and translate it to English. Return format: 'LANG_CODE | TRANSLATED_TEXT'. Query: {query}"
    lang_res = await gemini_service.generate_response(lang_info_prompt)
    
    try:
        lang_code, translated_query = [s.strip() for s in lang_res.split('|', 1)]
    except:
        lang_code, translated_query = "en", query

    # 2. Retrieve Context (Hybrid)
    contexts: List[ChunkContext] = await retrieve_context(db, translated_query)
    
    if not contexts:
        # Knowledge Gap!
        await _log_unanswered(db, query, user_id)
        return AnswerResponse(
            answer="I'm sorry, I don't have any verified information to answer that question.",
            citations=[],
            language=lang_code
        )

    context_text = ""
    for i, c in enumerate(contexts):
        context_text += f"[Source {i+1}]: {c.content}\n\n"

    # 3. Generate Grounded Answer
    system_prompt = (
        "You are Asila, a verified government assistant. "
        "Answer the question ONLY using the provided context. "
        "At the end of your answer, list the sources used in the format 'Sources: [1], [2]'. "
        "If the information is missing, say you don't know and do not hallucinate."
    )
    
    final_prompt = f"{system_prompt}\n\nContext:\n{context_text}\n\nUser Question: {translated_query}"
    english_answer = await gemini_service.generate_response(final_prompt)

    # 4. Handle "I don't know" cases from LLM
    if "don't know" in english_answer.lower() or "not in the context" in english_answer.lower():
        await _log_unanswered(db, query, user_id)

    # 5. Translate back to native language if not English
    final_answer = english_answer
    if lang_code.lower() != "en" and lang_code.lower() != "english":
        translate_back_prompt = f"Translate this text to {lang_code}: {english_answer}"
        final_answer = await gemini_service.generate_response(translate_back_prompt)

    # 6. Map Citations
    citations = [
        Citation(
            document_id=c.document_id,
            document_title=c.document_title,
            page_number=c.page_number
        ) for c in contexts
    ]

    return AnswerResponse(
        answer=final_answer,
        citations=citations,
        language=lang_code
    )

async def _log_unanswered(db: AsyncSession, query: str, user_id: str = None):
    uq = UnansweredQuery(user_id=user_id, question=query)
    db.add(uq)
    await db.commit()
