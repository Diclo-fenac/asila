from fastapi import FastAPI, Request, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.security.auth import auth_manager, get_current_user
from core.tenant.resolver import resolve_tenant
from core.database.tenant_session import get_tenant_db

from api.routes import auth, tenants, documents, chat, users, analytics, conversations
from core.exceptions.handlers import global_exception_handler
from core.logging.config import logger
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
        if request.method == "OPTIONS" or any(request.url.path.startswith(p) for p in ["/api/v1/health", "/docs", "/openapi.json", "/api/v1/tenants"]):
            return await call_next(request)
            
        # Try to get tenant from header X-Tenant-Id or from JWT org_id
        tenant_id = request.headers.get("X-Tenant-Id")
        
        if not tenant_id:
            auth_header = request.headers.get("Authorization")
            token = None
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            elif "access_token" in request.cookies:
                token = request.cookies.get("access_token")
                
            if token:
                try:
                    # Securely verify the token signature before extracting tenant routing info
                    payload = await auth_manager.verify_jwt(token)
                    tenant_id = payload.get("org_id")
                except:
                    pass

        if not tenant_id and request.url.path.startswith(("/api/v1/documents", "/api/v1/chat")):
            return JSONResponse(status_code=401, content={"detail": "Tenant context required (X-Tenant-Id header or token org_id)"})
            
        if tenant_id:
            try:
                request.state.tenant_id = tenant_id
                request.state.tenant_db_url = await resolve_tenant(tenant_id)
            except HTTPException as e:
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            except Exception as e:
                return JSONResponse(status_code=500, content={"detail": f"Tenant resolution error: {str(e)}"})

        return await call_next(request)

import os

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_str:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
else:
    logger.warning("ALLOWED_ORIGINS not set. Falling back to localhost for CORS.")
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(title="Asila API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TenancyMiddleware)
app.add_exception_handler(Exception, global_exception_handler)

# Include Routers
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(users.router)
api_router.include_router(analytics.router)
api_router.include_router(conversations.router)

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(api_router)
