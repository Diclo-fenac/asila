from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import json

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user
from core.security.rate_limit import limiter
from services.generation.service import answer_query, AnswerResponse
from services.analytics.service import track_query_for_crisis
from domain.tenant.queries.models import Query

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    query: str

@router.post("/query", response_model=AnswerResponse)
@limiter.limit("5/minute")
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
    tenant_id = getattr(request.state, "tenant_id", "org_test_123")

    # 1. Answer via RAG
    response = await answer_query(db, chat_data.query, user_id=current_user.get("sub"))

    # 2. Track for crisis (fire and forget or background)
    await track_query_for_crisis(tenant_id, chat_data.query)

    return response

@router.post("/query/stream")
@limiter.limit("5/minute")
async def query_asila_stream(
    request: Request,
    chat_data: ChatRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    tenant_id = getattr(request.state, "tenant_id", "org_test_123")
    
    async def generate():
        response = await answer_query(db, chat_data.query, user_id=current_user.get("sub"))
        await track_query_for_crisis(tenant_id, chat_data.query)
        yield f"data: {json.dumps(response.model_dump())}\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/query/history")
async def get_history(
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    stmt = select(Query).where(Query.user_id == user_id).order_by(Query.created_at.desc()).limit(50)
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
    return messages

class FeedbackRequest(BaseModel):
    message_id: str
    feedback: str

@router.post("/query/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    return {"status": "ok"}

