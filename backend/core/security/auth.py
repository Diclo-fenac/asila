import re
import bcrypt
from core.database.redis_client import redis_client
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
import uuid
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from core.config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

token_auth_scheme = HTTPBearer()

ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY



def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

def is_password_strong(password: str) -> bool:
    """
    Check if the password meets strength requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "access", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(days=7))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class AuthManager:
    async def verify_jwt(self, token: str, token_type: str = "access"):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                raise HTTPException(status_code=401, detail="Invalid token type")
            
            # Check if token is blacklisted via jti
            jti = payload.get("jti")
            if jti:
                is_blacklisted = await redis_client.get(f"bl_{jti}")
                if is_blacklisted:
                    raise HTTPException(status_code=401, detail="Token has been revoked")
                
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    async def revoke_token(self, token: str, expires_in: int):
        """Blacklist a token until it naturally expires."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti:
                await redis_client.setex(f"bl_{jti}", expires_in, "revoked")
        except JWTError:
            pass

auth_manager = AuthManager()

from fastapi import Request

async def get_current_user(request: Request):
    access_token = request.cookies.get("access_token")
    if not access_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return await auth_manager.verify_jwt(access_token, token_type="access")

def require_role(roles: list[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if not user_role or user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

from fastapi import Header
async def require_platform_admin(x_platform_key: str = Header(None)):
    import secrets
    platform_key = getattr(settings, "PLATFORM_API_KEY", "super-secret-platform-key")
    if not x_platform_key or not secrets.compare_digest(x_platform_key, platform_key):
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return True
