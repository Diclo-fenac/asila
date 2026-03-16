import httpx
from jose import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config.settings import settings

token_auth_scheme = HTTPBearer()

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
