import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from api.routes import api_keys, conversations_core, knowledge, mcp_core, organizations_core, provider_credentials, service_accounts, setup
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


@api_router.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "asila-api"}


@api_router.get("/health/ready", tags=["system"])
async def readiness_check():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with app_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Asila dependencies are not ready",
        ) from exc
    finally:
        await redis.aclose()
    return {"status": "ready", "service": "asila-api"}


app.include_router(api_router)
app.mount("/mcp", mcp_core.mcp_app())
