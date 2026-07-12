from fastapi import FastAPI, Request, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.security.auth import auth_manager, get_current_user
from core.tenant.resolver import resolve_tenant
from core.database.tenant_session import get_tenant_db
from core.tenant.context import tenant_context, tenant_key_hash, tenant_ip

from api.routes import auth, tenants, documents, chat, users, analytics, conversations, tasks
from core.exceptions.handlers import global_exception_handler
from core.logging.config import logger
from core.config.settings import settings as app_settings
import time
import os

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
            
        client_ip = request.client.host if request.client else ""
        tenant_ip.set(client_ip)
        
        # Try to get tenant from header X-Tenant-Id or from JWT org_id
        tenant_id = request.headers.get("X-Tenant-Id")
        api_key = request.headers.get("asila-api-key")
        
        import secrets
        master_key = app_settings.ASILA_MASTER_KEY
        if api_key and master_key and secrets.compare_digest(api_key, master_key):
            tenant_context.set("ADMIN")
            # Don't require tenant_db_url for admin
            return await call_next(request)
        
        if not tenant_id and api_key:
            from core.database.platform_session import PlatformSessionLocal
            from domain.platform.tenants.models import Tenant
            from sqlalchemy import select
            import hashlib
            
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            async with PlatformSessionLocal() as session:
                result = await session.execute(select(Tenant).where(Tenant.api_key_hash == api_key_hash))
                tenant = result.scalar_one_or_none()
                if tenant:
                    import ipaddress
                    if tenant.allowed_ips:
                        ip_allowed = False
                        try:
                            req_ip = ipaddress.ip_address(client_ip)
                            for cidr in tenant.allowed_ips:
                                if req_ip in ipaddress.ip_network(cidr):
                                    ip_allowed = True
                                    break
                        except ValueError:
                            pass
                        
                        if not ip_allowed:
                            from starlette.responses import JSONResponse
                            return JSONResponse(status_code=403, content={"detail": "IP address not allowed", "type": "AuthError"})
                    
                    tenant_id = tenant.id
                    tenant_key_hash.set(api_key_hash)
                    
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
                except Exception:
                    pass
                    
            if not tenant_id and "refresh_token" in request.cookies:
                try:
                    payload = await auth_manager.verify_jwt(request.cookies.get("refresh_token"), token_type="refresh")
                    tenant_id = payload.get("org_id")
                except Exception:
                    pass

        if not tenant_id and request.url.path.startswith(("/api/v1/documents", "/api/v1/chat", "/mcp")):
            if request.url.path.startswith("/mcp"):
                return JSONResponse(status_code=401, content={"detail": "Authentication failed: invalid API key.", "type": "AuthError"})
            return JSONResponse(status_code=401, content={"detail": "Tenant context required (X-Tenant-Id header or token org_id)"})
            
        if tenant_id:
            try:
                request.state.tenant_id = tenant_id
                request.state.tenant_db_url = await resolve_tenant(tenant_id)
                tenant_context.set(tenant_id)
            except HTTPException as e:
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            except Exception as e:
                return JSONResponse(status_code=500, content={"detail": f"Tenant resolution error: {str(e)}"})

        return await call_next(request)

if app_settings.ALLOWED_ORIGINS:
    allowed_origins = [origin.strip() for origin in app_settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
else:
    logger.warning("ALLOWED_ORIGINS not set. Falling back to localhost for CORS.")
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if app_settings.GOOGLE_API_KEY:
        logger.info("✅ GOOGLE_API_KEY loaded")
    else:
        logger.error("❌ GOOGLE_API_KEY missing - check .env")

    # Startup: ensure default tenant and ingest welcome.md
    from core.database.platform_session import PlatformSessionLocal
    from domain.platform.tenants.models import Tenant
    from sqlalchemy import select
    import secrets
    
    master_key = app_settings.ASILA_MASTER_KEY
    if master_key:
        async with PlatformSessionLocal() as session:
            result = await session.execute(select(Tenant).where(Tenant.name == "Default Tenant"))
            tenant = result.scalar_one_or_none()
            if not tenant:
                try:
                    import hashlib
                    raw_api_key = f"sk-asila-{secrets.token_urlsafe(32)}"
                    api_key_hash = hashlib.sha256(raw_api_key.encode()).hexdigest()
                    logger.info(f"Generated Default Tenant API Key (Save this!): {raw_api_key}")
                    
                    tenant = Tenant(
                        id="org_default",
                        name="Default Tenant",
                        db_connection_string="postgresql+asyncpg://asila:asila@postgres:5432/asila_shared",
                        api_key_hash=api_key_hash
                    )
                    session.add(tenant)
                    await session.commit()
                except Exception:
                    await session.rollback()
                
            from core.database.tenant_session import manager
            try:
                pass
                # await manager.create_tenant_schema("org_default")
            except Exception as e:
                logger.error(f"Failed to create schema for org_default: {e}")

            # Trigger ingestion if welcome.md exists
            if os.path.exists("welcome.md"):
                from services.ingestion.service import process_document
                SessionMaker = await manager.get_tenant_sessionmaker("org_default")
                async with SessionMaker() as db:
                        with open("welcome.md", "r") as f:
                            content = f.read()
                        try:
                            await process_document(
                                db=db,
                                tenant_id="org_default",
                                title="Welcome to Asila",
                                content=content,
                                file_name="welcome.md"
                            )
                        except Exception as e:
                            logger.error(f"Failed to auto-ingest welcome.md: {e}")
    yield

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def get_rate_limit_key(request: Request) -> str:
    # Use tenant_id if authenticated, fallback to IP address
    tenant_id = tenant_context.get()
    if tenant_id:
        return f"tenant:{tenant_id}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key, default_limits=["60/minute"])

app = FastAPI(title="Asila API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
api_router.include_router(tasks.router)

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(api_router)

# Mount FastMCP SSE Endpoint
from api.routes.mcp import mcp_server
# sse_app handles both GET /sse and POST /messages
app.mount("/mcp", mcp_server.sse_app())
