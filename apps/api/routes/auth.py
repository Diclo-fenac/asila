from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from core.security.auth import create_access_token, get_password_hash, verify_password
from core.database.tenant_session import get_tenant_db
from domain.tenant.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_tenant_db),
    tenant_id: str = None # Usually passed in header via middleware, but can be explicit
):
    stmt = select(User).where(User.id == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract tenant_id from context (middleware should have resolved it)
    # If not provided explicitly, we use a fallback or error
    
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user.id, "org_id": tenant_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signup")
async def signup(
    username: str, 
    password: str, 
    name: str = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    hashed_password = get_password_hash(password)
    new_user = User(
        id=username, 
        name=name, 
        password_hash=hashed_password
    )
    db.add(new_user)
    await db.commit()
    return {"msg": "User created successfully"}
