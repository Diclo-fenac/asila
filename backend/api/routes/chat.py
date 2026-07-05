from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import json

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user
from services.generation.service import answer_query, AnswerResponse, answer_query_stream
from services.analytics.service import track_query_for_crisis
from domain.tenant.queries.models import Query

router = APIRouter(prefix="/chat", tags=["chat"])

from typing import Optional

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None

@router.post("/query", response_model=AnswerResponse)
async def query_asila(
    request: Request,
    chat_data: ChatRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    """
    Advanced RAG query endpoint with multi-language support, 
    citations, and crisis detection.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=500, detail="Tenant context missing")

    # 1. Answer via RAG
    response = await answer_query(db, chat_data.query, user_id=current_user.get("sub"), conversation_id=chat_data.conversation_id)

    # 2. Track for crisis (fire and forget or background)
    await track_query_for_crisis(tenant_id, chat_data.query)

    return response

@router.post("/query/stream")
async def query_asila_stream(
    request: Request,
    chat_data: ChatRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=500, detail="Tenant context missing")
    
    async def generate():
        async for event in answer_query_stream(db, chat_data.query, user_id=current_user.get("sub"), conversation_id=chat_data.conversation_id):
            yield f"data: {json.dumps(event)}\n\n"
        await track_query_for_crisis(tenant_id, chat_data.query)
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/query/history")
async def get_history(
    conversation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    stmt = select(Query).where(Query.user_id == user_id)
    if conversation_id:
        stmt = stmt.where(Query.conversation_id == conversation_id)
    stmt = stmt.order_by(Query.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    queries = result.scalars().all()
    
    messages = []
    for q in queries:
        messages.append({
            "id": f"q-{q.id}",
            "role": "user",
            "content": q.question,
            "created_at": q.created_at.isoformat()
        })
        messages.append({
            "id": f"a-{q.id}",
            "role": "assistant",
            "content": q.answer,
            "created_at": q.created_at.isoformat()
        })
    # Messages were fetched desc (newest first). Since history is usually shown oldest to newest,
    # let's return them as they are but frontend handles ordering if needed.
    # Actually, previous implementation returned desc. We'll leave it.
    return messages

class FeedbackRequest(BaseModel):
    message_id: str
    feedback: str

@router.post("/query/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    return {"status": "ok"}

