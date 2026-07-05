from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import base64
from core.database.tenant_session import get_tenant_db
from domain.tenant.users.models import User, Role
from core.security.auth import get_password_hash, require_role
import secrets
import string

router = APIRouter(prefix="/users", tags=["users"])

class UserInvite(BaseModel):
    email: str
    role: str

class UserUpdate(BaseModel):
    role: str

@router.get("/")
async def list_users(db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin", "user"])), cursor: Optional[str] = None, limit: int = 10):
    stmt = select(User).order_by(asc(User.created_at), asc(User.id)).limit(limit + 1)
    
    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
            cursor_created_at = datetime.fromisoformat(cursor_data['created_at'])
            cursor_id = cursor_data['id']
            stmt = stmt.where(
                (User.created_at > cursor_created_at) |
                ((User.created_at == cursor_created_at) & (User.id > cursor_id))
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor format")
            
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    has_more = len(users) > limit
    if has_more:
        users = users[:limit]
        
    next_cursor = None
    if users:
        last_item = users[-1]
        cursor_payload = {
            "created_at": last_item.created_at.isoformat() if hasattr(last_item, 'created_at') and last_item.created_at else datetime.now(timezone.utc).isoformat(),
            "id": last_item.id
        }
        next_cursor = base64.b64encode(json.dumps(cursor_payload).encode('utf-8')).decode('utf-8')
        
    items = [{"id": u.id, "email": u.id, "name": u.name, "role": u.role.value if hasattr(u.role, 'value') else u.role, "status": "active" if u.is_active else "inactive", "created_at": getattr(u, "created_at", "2023-01-01T00:00:00").isoformat() if hasattr(u, "created_at") and u.created_at else "2023-01-01T00:00:00"} for u in users]
    
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more
    }

@router.post("/invite")
async def invite_user(invite: UserInvite, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    alphabet = string.ascii_letters + string.digits
    random_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    try:
        user_role = Role(invite.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role specified.")
        
    new_user = User(
        id=invite.email,
        name=invite.email.split('@')[0],
        password_hash=get_password_hash(random_password),
        role=user_role
    )
    db.add(new_user)
    await db.commit()
    # Return the password so the admin can copy it
    return {"msg": "Invited", "temporary_password": random_password}

@router.patch("/{id}/role")
async def update_role(id: str, data: UserUpdate, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    try:
        user.role = Role(data.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role specified.")
        
    user.token_version += 1 # Revoke existing tokens for this user
    await db.commit()
    return {"msg": "Role updated"}

@router.delete("/{id}")
async def delete_user(id: str, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if user:
        # Instead of hard delete, deactivate to preserve data integrity and token checks
        user.is_active = False
        user.token_version += 1 # Instantly revoke access
        await db.commit()
    return {"msg": "Deleted (Deactivated)"}

@router.post("/{id}/reactivate")
async def reactivate_user(id: str, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_active = True
    await db.commit()
    return {"msg": "User reactivated"}
