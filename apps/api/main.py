from fastapi import FastAPI, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.security.auth import auth_manager, get_current_user
from core.tenant.resolver import resolve_tenant
from core.database.tenant_session import get_tenant_db

class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing auth header"})
            
        token = auth_header.split(" ")[1]
        try:
            # For routing, we peek at org_id (verification happens later in dependency)
            from jose import jwt
            payload = jwt.get_unverified_claims(token)
            org_id = payload.get("org_id")
            if not org_id:
                return JSONResponse(status_code=401, content={"detail": "Missing org_id in token"})
            request.state.tenant_db_url = await resolve_tenant(org_id)
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})

        return await call_next(request)

app = FastAPI(title="Asila API")
app.add_middleware(TenancyMiddleware)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/tenant/verify", dependencies=[Depends(get_current_user)])
async def verify(db=Depends(get_tenant_db)):
    return {"status": "success"}
