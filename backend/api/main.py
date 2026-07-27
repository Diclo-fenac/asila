import time
from contextlib import asynccontextmanager
from uuid import uuid4
import asyncio
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from api.routes import api_keys, audit, conversations_core, knowledge, mcp_core, organizations_core, provider_credentials, service_accounts, setup
from core.config.settings import settings
from core.database.app_session import app_engine
from core.exceptions.handlers import global_exception_handler
from core.logging.config import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_processed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            organization_id=getattr(request.state, "organization_id", None),
            request_id=request_id,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow health checks to bypass rate limits
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)
            
        identifier = getattr(request.state, "organization_id", request.client.host if request.client else "unknown")
        rate_limit_key = f"rate_limit:{identifier}"
        
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            current = await redis.incr(rate_limit_key)
            if current == 1:
                await redis.expire(rate_limit_key, 60)
            
            if current > 300:  # 300 requests per minute
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests", "type": "RateLimitExceeded"},
                    headers={"Retry-After": "60"}
                )
        except Exception as e:
            logger.warning(f"Rate limiting failed: {e}")
        finally:
            if 'redis' in locals():
                await redis.aclose()
                
        return await call_next(request)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "asila_started",
        environment=settings.ENVIRONMENT,
        local_setup_enabled=bool(settings.ASILA_SETUP_TOKEN),
    )
    yield
    logger.info("asila_stopped")


allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app = FastAPI(
    title="Asila Knowledge Platform API",
    version="0.2.0",
    description="Open-source, local-first knowledge infrastructure for AI systems.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Asila-API-Key",
        "X-Organization-Id",
        "X-Request-ID",
    ],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_exception_handler(Exception, global_exception_handler)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(setup.router)
api_router.include_router(organizations_core.router)
api_router.include_router(knowledge.router)
api_router.include_router(conversations_core.router)
api_router.include_router(api_keys.router)
api_router.include_router(provider_credentials.router)
api_router.include_router(service_accounts.router)
api_router.include_router(audit.router)


@api_router.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "asila-api"}


@api_router.get("/health/ready", tags=["system"])
async def readiness_check():
    async def check_postgres():
        start = time.perf_counter()
        try:
            async with app_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000), "details": "DB connection successful"}
        except Exception as e:
            return {"status": "down", "latency_ms": round((time.perf_counter() - start) * 1000), "details": str(e)}

    async def check_redis():
        start = time.perf_counter()
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await redis.ping()
            await redis.aclose()
            return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000), "details": "Queue responsive"}
        except Exception as e:
            return {"status": "down", "latency_ms": round((time.perf_counter() - start) * 1000), "details": str(e)}

    async def check_ollama():
        start = time.perf_counter()
        try:
            # We assume Ollama base URL is configured, defaulting to what's in settings if possible.
            # Using httpx to hit ollama
            ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://ollama:11434")
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                resp.raise_for_status()
            return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000), "details": "Ollama responsive"}
        except Exception as e:
            return {"status": "down", "latency_ms": round((time.perf_counter() - start) * 1000), "details": str(e)}

    async def check_docling():
        start = time.perf_counter()
        try:
            import os
            docling_url = os.getenv("DOCLING_URL", "http://docling:5001")
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{docling_url}/health")
                resp.raise_for_status()
            return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000), "details": "DocumentConverter ready"}
        except Exception as e:
            return {"status": "down", "latency_ms": round((time.perf_counter() - start) * 1000), "details": str(e)}

    results = await asyncio.gather(
        asyncio.wait_for(check_postgres(), timeout=2.0),
        asyncio.wait_for(check_redis(), timeout=2.0),
        asyncio.wait_for(check_ollama(), timeout=2.0),
        asyncio.wait_for(check_docling(), timeout=2.0),
        return_exceptions=True
    )
    
    # Process results, handling TimeoutErrors from wait_for
    def process_result(res, name):
        if isinstance(res, Exception):
            return {"status": "down", "latency_ms": 2000, "details": "Timeout or unhandled error"}
        return res

    pg_res = process_result(results[0], "postgresql")
    rd_res = process_result(results[1], "redis")
    ol_res = process_result(results[2], "ollama")
    dl_res = process_result(results[3], "docling")

    services = {
        "postgresql": pg_res,
        "redis": rd_res,
        "ollama": ol_res,
        "docling": dl_res
    }

    if pg_res["status"] == "down" or rd_res["status"] == "down":
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif ol_res["status"] == "down" or dl_res["status"] == "down":
        overall_status = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        status_code = status.HTTP_200_OK

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services
        }
    )


app.include_router(api_router)
app.mount("/mcp", mcp_core.mcp_app())
