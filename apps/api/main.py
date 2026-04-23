from fastapi import FastAPI, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.security.auth import auth_manager, get_current_user
from core.tenant.resolver import resolve_tenant
from core.database.tenant_session import get_tenant_db

from apps.api.routes import auth, tenants, documents, chat
from core.exceptions.handlers import global_exception_handler
from core.logging.config import logger
from core.security.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import time

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            "request_processed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s",
            tenant_id=getattr(request.state, "tenant_id", None)
        )
        return response

class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Paths that don't need tenant resolution
        if request.url.path in ["/health", "/docs", "/openapi.json", "/auth/token", "/tenants/"]:
            return await call_next(request)
            
        # Try to get tenant from header X-Tenant-Id or from JWT org_id
        tenant_id = request.headers.get("X-Tenant-Id")
        
        if not tenant_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    from jose import jwt
                    # Peek at the token without full verification just for routing
                    payload = jwt.get_unverified_claims(token)
                    tenant_id = payload.get("org_id")
                except:
                    pass

        if not tenant_id and request.url.path.startswith(("/documents", "/chat")):
            return JSONResponse(status_code=401, content={"detail": "Tenant context required (X-Tenant-Id header or token org_id)"})
            
        if tenant_id:
            try:
                request.state.tenant_id = tenant_id
                request.state.tenant_db_url = await resolve_tenant(tenant_id)
            except Exception as e:
                return JSONResponse(status_code=404, content={"detail": f"Tenant not found: {str(e)}"})

        return await call_next(request)

app = FastAPI(title="Asila API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TenancyMiddleware)
app.add_exception_handler(Exception, global_exception_handler)

# Include Routers
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(documents.router)
app.include_router(chat.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
