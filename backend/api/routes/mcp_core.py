from contextlib import contextmanager
from contextvars import ContextVar
import json
from typing import Literal

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import Context, FastMCP
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.database.app_session import AppSessionLocal, set_transaction_organization
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from core.organization.context import organization_scope
from domain.app.documents.models import Document, DocumentStatus
from domain.app.repositories.models import Repository
from services.retrieval.service import keyword_search, normalize_search_limit, validate_query
from services.ai.factory import build_organization_embedding_provider
from services.retrieval.service import hybrid_search


mcp_server = FastMCP("Asila")
_MCP_PRINCIPAL: ContextVar[Principal | None] = ContextVar(
    "mcp_principal", default=None
)


@contextmanager
def _principal_scope(principal: Principal):
    token = _MCP_PRINCIPAL.set(principal)
    try:
        yield
    finally:
        _MCP_PRINCIPAL.reset(token)


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            principal = await get_current_principal(request)
            if not principal.organization_id:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "An organization-scoped credential is required"},
                )
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        except Exception:
            from core.logging.config import logger

            logger.exception("mcp_authentication_failed")
            return JSONResponse(
                status_code=500,
                content={"detail": "MCP authentication service unavailable"},
            )

        with _principal_scope(principal), organization_scope(principal.organization_id):
            return await call_next(request)


def _principal_from_context(ctx: Context) -> Principal:
    principal = _MCP_PRINCIPAL.get()
    if principal is None:
        raise RuntimeError("MCP principal is unavailable")
    return principal


async def _search_for_principal(
    principal: Principal, query: str, limit: int, mode: Literal["keyword", "hybrid"]
) -> list[dict]:
    if not principal.has_scope("search:read"):
        raise PermissionError("Missing scope: search:read")
    organization_id = principal.organization_id
    if organization_id is None:
        raise PermissionError("Organization context is required")

    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(organization_id):
                await set_transaction_organization(session, organization_id)
                if mode == "hybrid":
                    results = await hybrid_search(
                        session,
                        query,
                        provider=await build_organization_embedding_provider(organization_id),
                        limit=limit,
                    )
                else:
                    results = await keyword_search(session, query, limit=limit)
                return [result.as_dict() for result in results]


@mcp_server.tool(name="asila_list_repositories")
async def list_repositories(ctx: Context) -> str:
    principal = _principal_from_context(ctx)
    if not principal.has_scope("repositories:read"):
        return json.dumps({"error": "Missing scope: repositories:read"})

    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(principal.organization_id):
                await set_transaction_organization(session, principal.organization_id)
                result = await session.execute(
                    select(Repository).order_by(Repository.created_at.desc())
                )
                return json.dumps(
                    [
                        {
                            "id": repo.id,
                            "name": repo.name,
                            "connector_type": repo.connector_type,
                            "external_id": repo.external_id,
                        }
                        for repo in result.scalars().all()
                    ]
                )


@mcp_server.tool(name="asila_search")
async def search(
    query: str,
    top_k: int = 10,
    mode: Literal["keyword", "hybrid"] = "keyword",
    ctx: Context | None = None,
) -> str:
    if ctx is None:
        return json.dumps({"error": "MCP request context is required"})
    try:
        results = await _search_for_principal(
            _principal_from_context(ctx),
            validate_query(query),
            normalize_search_limit(top_k),
            mode,
        )
        return json.dumps({"query": query, "results": results})
    except (PermissionError, ValueError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)})


@mcp_server.tool(name="asila_get_document")
async def get_document(document_id: str, ctx: Context | None = None) -> str:
    if ctx is None:
        return json.dumps({"error": "MCP request context is required"})
    principal = _principal_from_context(ctx)
    if not principal.has_scope("search:read"):
        return json.dumps({"error": "Missing scope: search:read"})

    async with AppSessionLocal() as session:
        async with session.begin():
            with organization_scope(principal.organization_id):
                await set_transaction_organization(session, principal.organization_id)
                result = await session.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()
                if document is None or document.status == DocumentStatus.DELETED:
                    return json.dumps({"error": "Document not found"})
                return json.dumps(
                    {
                        "id": document.id,
                        "title": document.title,
                        "source_uri": document.source_uri,
                        "status": document.status.value,
                        "content": document.extracted_text,
                    }
                )


def mcp_app():
    app = mcp_server.sse_app()
    app.add_middleware(MCPAuthMiddleware)
    return app
