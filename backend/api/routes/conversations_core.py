from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.app_session import get_app_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.app.conversations.models import MessageRole
from services.ai.factory import (
    build_organization_embedding_provider,
    build_organization_generation_provider,
)
from services.conversations.service import (
    answer_question,
    append_message,
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)


router = APIRouter(prefix="/knowledge/conversations", tags=["conversations"])


def require_conversation_scope(principal: Principal, scope: str) -> None:
    if not principal.has_scope(scope):
        raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=512)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    generate: bool = False
    mode: Literal["keyword", "hybrid"] = "keyword"


def conversation_response(conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "archived": conversation.archived,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


def message_response(message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role.value,
        "content": message.content,
        "citations": message.citations,
        "provider": message.provider,
        "model": message.model,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation_route(
    data: ConversationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_conversation_scope(principal, "conversations:write")
    try:
        conversation = await create_conversation(
            db,
            organization_id=request.state.organization_id,
            title=data.title,
            created_by_user_id=principal.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return conversation_response(conversation)


@router.get("")
async def list_conversations_route(
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
    limit: int = Query(default=50, ge=1, le=200),
):
    require_conversation_scope(principal, "conversations:read")
    conversations = await list_conversations(
        db,
        organization_id=request.state.organization_id,
        limit=limit,
    )
    return [conversation_response(item) for item in conversations]


@router.get("/{conversation_id}")
async def get_conversation_route(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_conversation_scope(principal, "conversations:read")
    conversation = await get_conversation(
        db,
        organization_id=request.state.organization_id,
        conversation_id=conversation_id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await list_messages(
        db,
        organization_id=request.state.organization_id,
        conversation_id=conversation_id,
    )
    return {
        **conversation_response(conversation),
        "messages": [message_response(item) for item in messages],
    }


@router.post("/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def append_conversation_message_route(
    conversation_id: str,
    data: MessageCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_conversation_scope(principal, "conversations:write")
    try:
        if data.generate:
            user_message, assistant_message, citations = await answer_question(
                db,
                organization_id=request.state.organization_id,
                conversation_id=conversation_id,
                question=data.content,
                generation_provider=await build_organization_generation_provider(request.state.organization_id),
                embedding_provider=(
                    await build_organization_embedding_provider(request.state.organization_id)
                    if data.mode == "hybrid"
                    else None
                ),
                mode=data.mode,
            )
            return {
                "user_message": message_response(user_message),
                "assistant_message": message_response(assistant_message),
                "citations": citations,
            }
        message = await append_message(
            db,
            organization_id=request.state.organization_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=data.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"message": message_response(message), "citations": []}
