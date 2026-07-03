from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database.tenant_session import get_tenant_db
from domain.tenant.users.models import User
from core.security.auth import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])

class UserInvite(BaseModel):
    email: str
    role: str

class UserUpdate(BaseModel):
    role: str

@router.get("/")
async def list_users(db: AsyncSession = Depends(get_tenant_db), page: int = 1, limit: int = 10):
    result = await db.execute(select(User).limit(limit).offset((page-1)*limit))
    users = result.scalars().all()
    items = [{"id": u.id, "email": u.id, "name": u.name, "role": getattr(u, "role", "user"), "status": "active", "created_at": getattr(u, "created_at", "2023-01-01T00:00:00").isoformat() if hasattr(u, "created_at") else "2023-01-01T00:00:00"} for u in users]
    return {
        "items": items,
        "total": len(users),
        "page": page,
        "page_size": limit
    }

@router.post("/invite")
async def invite_user(invite: UserInvite, db: AsyncSession = Depends(get_tenant_db)):
    new_user = User(
        id=invite.email,
        name=invite.email.split('@')[0],
        password_hash=get_password_hash("password")
    )
    db.add(new_user)
    await db.commit()
    return {"msg": "Invited"}

@router.patch("/{id}/role")
async def update_role(id: str, data: UserUpdate, db: AsyncSession = Depends(get_tenant_db)):
    return {"msg": "Role updated"}

@router.delete("/{id}")
async def delete_user(id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()
    return {"msg": "Deleted"}
