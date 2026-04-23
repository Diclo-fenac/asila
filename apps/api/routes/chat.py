from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user
from core.security.rate_limit import limiter
from services.generation.service import answer_query, AnswerResponse
from services.analytics.service import track_query_for_crisis

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
...
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

