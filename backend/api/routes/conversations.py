from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, ConfigDict
from typing import List

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user
from domain.tenant.conversations.models import Conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class ConversationUpdate(BaseModel):
    title: str

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat()
        )
        for c in conversations
    ]

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    
    from domain.tenant.users.models import User
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        new_user = User(id=user_id, name=user_id.split("@")[0])
        db.add(new_user)
        await db.flush()

    new_conv = Conversation(user_id=user_id, title="New Conversation")
    db.add(new_conv)
    await db.commit()
    await db.refresh(new_conv)
    
    return ConversationResponse(
        id=new_conv.id,
        title=new_conv.title,
        created_at=new_conv.created_at.isoformat()
    )

@router.patch("/{id}", response_model=ConversationResponse)
async def rename_conversation(
    id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    stmt = select(Conversation).where(Conversation.id == id, Conversation.user_id == user_id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conv.title = data.title
    await db.commit()
    
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat()
    )

@router.delete("/{id}")
async def delete_conversation(
    id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    stmt = select(Conversation).where(Conversation.id == id, Conversation.user_id == user_id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    await db.delete(conv)
    await db.commit()
    
    return {"msg": "Deleted"}
