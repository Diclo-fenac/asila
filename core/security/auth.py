from datetime import datetime, timedelta
from typing import Optional
import httpx
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
token_auth_scheme = HTTPBearer()

ALGORITHM = "HS256"
SECRET_KEY = "dev-secret-key" # In production, use settings.SECRET_KEY

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class AuthManager:
    _jwks = None

    async def get_jwks(self):
        if self._jwks is None:
            url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                self._jwks = resp.json()
        return self._jwks

    async def verify_jwt(self, token: str):
        jwks = await self.get_jwks()
        try:
            return jwt.decode(
                token, jwks, algorithms=["RS256"],
                audience=settings.AUTH0_AUDIENCE,
                issuer=f"https://{settings.AUTH0_DOMAIN}/"
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

auth_manager = AuthManager()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)):
    return await auth_manager.verify_jwt(token.credentials)
