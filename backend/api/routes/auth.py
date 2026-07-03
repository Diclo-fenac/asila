from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from core.security.auth import create_access_token, get_password_hash, verify_password
from core.database.tenant_session import get_tenant_db
from domain.tenant.users.models import User

from pydantic import BaseModel
from core.security.auth import get_current_user

class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    tenant_id: str

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    stmt = select(User).where(User.id == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user.id, "org_id": request.tenant_id},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "role": getattr(user, "role", "user")},
        "tenant": {"id": request.tenant_id}
    }

@router.post("/register")
async def signup(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    hashed_password = get_password_hash(request.password)
    new_user = User(
        id=request.email, 
        name=request.name, 
        password_hash=hashed_password,
    )
    db.add(new_user)
    await db.commit()
    return {"msg": "User created successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    user_id = current_user.get("sub")
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
         raise HTTPException(status_code=404)
    return {"user": {"id": user.id, "name": user.name, "role": getattr(user, "role", "user")}}

@router.post("/logout")
async def logout():
    return {"msg": "logged out"}
