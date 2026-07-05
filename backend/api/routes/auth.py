from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
import re

from core.security.auth import (
    create_access_token, 
    create_refresh_token,
    get_password_hash, 
    verify_password,
    is_password_strong,
    auth_manager,
    get_current_user
)
from core.database.tenant_session import get_tenant_db
from domain.tenant.users.models import User
from core.security.audit import log_auth_event

from pydantic import BaseModel, EmailStr, constr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str

class RegisterRequest(BaseModel):
    name: constr(min_length=2, max_length=100, strip_whitespace=True)
    email: EmailStr
    password: str
    tenant_id: str

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    login_req: LoginRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    stmt = select(User).where(User.id == login_req.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_req.password, user.password_hash):
        await log_auth_event(
            event_type="login", email=login_req.email, tenant_id=login_req.tenant_id, 
            status="failed", ip_address=request.client.host, details="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=15)
    refresh_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        data={"sub": user.id, "org_id": login_req.tenant_id, "role": user.role.value if hasattr(user.role, 'value') else user.role, "token_version": user.token_version},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id, "org_id": login_req.tenant_id, "role": user.role.value if hasattr(user.role, 'value') else user.role, "token_version": user.token_version},
        expires_delta=refresh_token_expires
    )

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=15 * 60
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    await log_auth_event(
        event_type="login", email=user.id, tenant_id=login_req.tenant_id, 
        status="success", ip_address=request.client.host
    )

    return {
        "msg": "Login successful",
        "user": {"id": user.id, "name": user.name, "role": user.role.value if hasattr(user.role, 'value') else user.role},
        "tenant": {"id": login_req.tenant_id}
    }

@router.post("/register")
async def signup(
    request: Request,
    response: Response,
    reg_req: RegisterRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    if not is_password_strong(reg_req.password):
        await log_auth_event(
            event_type="register", email=reg_req.email, tenant_id=reg_req.tenant_id, 
            status="failed", ip_address=request.client.host, details="Weak password"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and a number."
        )

    # Check if user exists (to prevent 500 error & graceful error)
    stmt = select(User).where(User.id == reg_req.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        await log_auth_event(
            event_type="register", email=reg_req.email, tenant_id=reg_req.tenant_id, 
            status="failed", ip_address=request.client.host, details="User already exists"
        )
        # Avoid leaking exact user existence in high-security systems, but for this context a 400 is fine.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered"
        )

    hashed_password = get_password_hash(reg_req.password)
    new_user = User(
        id=reg_req.email, 
        name=reg_req.name, 
        password_hash=hashed_password,
    )
    db.add(new_user)
    
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed due to data conflict.")

    await log_auth_event(
        event_type="register", email=reg_req.email, tenant_id=reg_req.tenant_id, 
        status="success", ip_address=request.client.host
    )

    return {"msg": "User created successfully"}

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_tenant_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    # Verify refresh token
    payload = await auth_manager.verify_jwt(refresh_token, token_type="refresh")
    user_id = payload.get("sub")
    tenant_id = payload.get("org_id")

    # Verify user and token_version
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or deleted")
        
    token_version = payload.get("token_version")
    if token_version is None or token_version != user.token_version:
        raise HTTPException(status_code=401, detail="Token revoked (version mismatch)")

    # Issue new access token
    access_token_expires = timedelta(minutes=15)
    new_access_token = create_access_token(
        data={"sub": user_id, "org_id": tenant_id, "role": user.role.value if hasattr(user.role, 'value') else user.role, "token_version": user.token_version},
        expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=15 * 60
    )

    await log_auth_event(
        event_type="refresh", email=user_id, tenant_id=tenant_id, 
        status="success", ip_address=request.client.host
    )
    
    return {"msg": "Token refreshed"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    user_id = current_user.get("sub")
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
         
    return {"user": {"id": user.id, "name": user.name, "role": user.role.value if hasattr(user.role, 'value') else user.role}}

@router.post("/logout")
async def logout(request: Request, response: Response):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    email = "unknown"
    tenant_id = "unknown"

    if refresh_token:
        try:
            payload = await auth_manager.verify_jwt(refresh_token, token_type="refresh")
            email = payload.get("sub", "unknown")
            tenant_id = payload.get("org_id", "unknown")
            
            # Blacklist the refresh token for its remaining lifetime (7 days max)
            await auth_manager.revoke_token(refresh_token, expires_in=7 * 24 * 60 * 60)
        except Exception:
            pass # Ignore if token is already invalid/expired

    if access_token:
        try:
            # Blacklist access token for its remaining lifetime (15 mins max)
            await auth_manager.revoke_token(access_token, expires_in=15 * 60)
        except Exception:
            pass

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    await log_auth_event(
        event_type="logout", email=email, tenant_id=tenant_id, 
        status="success", ip_address=request.client.host
    )

    return {"msg": "Logged out successfully"}
