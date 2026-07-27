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
from core.exceptions.resilience import ServiceUnavailableError, BulkheadRejectedError
from core.resilience import circuit_breaker, bulkhead
from services.documents.service import create_document
from services.ingestion_jobs.service import create_or_get_job
from core.queue import enqueue_ingestion_job
from domain.app.ingestion_jobs.models import IngestionJob
from services.audit.service import record_audit_event


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


def _require_any_scope(principal: Principal, *scopes: str) -> None:
    if not any(principal.has_scope(s) for s in scopes):
        raise PermissionError(f"Missing required scope (any of: {', '.join(scopes)})")


async def _search_for_principal(
    principal: Principal, query: str, limit: int, mode: Literal["keyword", "hybrid"]
) -> list[dict]:
    _require_any_scope(principal, "search:read", "knowledge:search", "mcp:discover")
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
                res_dict = [result.as_dict() for result in results]
                await record_audit_event(
                    session,
                    action="mcp.tool_call",
                    actor_id=principal.service_account_id or principal.user_id or principal.subject,
                    organization_id=organization_id,
                    target_type="mcp_tool",
                    target_id="asila_search",
                    details={"query": query, "mode": mode, "result_count": len(res_dict)},
                )
                return res_dict


@mcp_server.tool(name="asila_list_repositories")
@circuit_breaker(name="postgresql", failure_threshold=5, recovery_timeout=30)
@bulkhead(name="postgresql_list_repo", max_concurrency=10)
async def list_sources(ctx: Context) -> str:
    """
    List all indexed repositories and data sources available for search in the current organization.
    
    Use this tool to see what knowledge bases are currently indexed before performing a search,
    or to find a specific repository_id to filter searches.

    Returns:
        JSON string containing a list of repositories, each with:
        - id: The repository UUID
        - name: The human-readable name
        - connector_type: The type of connector (e.g. 'local', 'github')
        - external_id: The external reference identifier
        
    Errors:
        Returns an error string if the database is temporarily unavailable due to circuit breakers
        or capacity limits. Wait the suggested time before retrying.
    """
    try:
        principal = _principal_from_context(ctx)
        _require_any_scope(principal, "repositories:read", "knowledge:read", "documents:list", "mcp:discover")

        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(principal.organization_id):
                    await set_transaction_organization(session, principal.organization_id)
                    result = await session.execute(
                        select(Repository).order_by(Repository.created_at.desc())
                    )
                    repos = [
                        {
                            "id": repo.id,
                            "name": repo.name,
                            "connector_type": repo.connector_type,
                            "external_id": repo.external_id,
                        }
                        for repo in result.scalars().all()
                    ]
                    await record_audit_event(
                        session,
                        action="mcp.tool_call",
                        actor_id=principal.service_account_id or principal.user_id or principal.subject,
                        organization_id=principal.organization_id,
                        target_type="mcp_tool",
                        target_id="asila_list_repositories",
                        details={"result_count": len(repos)},
                    )
                    return json.dumps(repos)
    except (ServiceUnavailableError, BulkheadRejectedError) as e:
        raise RuntimeError(f"Error: {e.message}")


@mcp_server.tool(name="asila_list_documents")
@circuit_breaker(name="postgresql", failure_threshold=5, recovery_timeout=30)
@bulkhead(name="postgresql_list_doc", max_concurrency=10)
async def list_documents(limit: int = 50, ctx: Context | None = None) -> str:
    """
    List indexed documents in the current organization knowledge base.

    Args:
        limit: Maximum number of documents to return (default: 50, max: 200).

    Returns:
        JSON string containing a list of documents with their id, title, source_uri, and status.
    """
    if ctx is None:
        raise ValueError("MCP request context is required")
    try:
        principal = _principal_from_context(ctx)
        _require_any_scope(principal, "search:read", "knowledge:read", "documents:list", "mcp:discover")

        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(principal.organization_id):
                    await set_transaction_organization(session, principal.organization_id)
                    result = await session.execute(
                        select(Document)
                        .where(Document.status != DocumentStatus.DELETED)
                        .order_by(Document.created_at.desc())
                        .limit(min(max(1, limit), 200))
                    )
                    docs = [
                        {
                            "id": doc.id,
                            "title": doc.title,
                            "source_uri": doc.source_uri,
                            "status": doc.status.value,
                        }
                        for doc in result.scalars().all()
                    ]
                    await record_audit_event(
                        session,
                        action="mcp.tool_call",
                        actor_id=principal.service_account_id or principal.user_id or principal.subject,
                        organization_id=principal.organization_id,
                        target_type="mcp_tool",
                        target_id="asila_list_documents",
                        details={"result_count": len(docs)},
                    )
                    return json.dumps(docs)
    except (ServiceUnavailableError, BulkheadRejectedError) as e:
        raise RuntimeError(f"Error: {e.message}")


@mcp_server.tool(name="asila_search")
@bulkhead(name="postgresql_search", max_concurrency=20)
async def search_knowledge(
    query: str,
    top_k: int = 10,
    mode: Literal["keyword", "hybrid"] = "hybrid",
    ctx: Context | None = None,
) -> str:
    """
    Search the organizational knowledge base across all documents and repositories.
    
    This tool provides hybrid search capabilities combining semantic embeddings and keyword matching.
    It automatically degrades to keyword-only search if the embedding service is unavailable.

    Args:
        query: The search query string. Should be descriptive and natural language.
        top_k: Maximum number of results to return (default: 10, max: 50).
        mode: The search mode. "hybrid" is recommended for best results. "keyword" forces exact match.
    
    Returns:
        JSON string containing matching text chunks, relevance scores, and document metadata.
        Large results may be truncated. If semantic search fails, a warning note is included
        in the output, but results will still be returned.
        
    Errors:
        Raises an error string if the database is completely unavailable.
    """
    if ctx is None:
        raise ValueError("MCP request context is required")
    try:
        results = await _search_for_principal(
            _principal_from_context(ctx),
            validate_query(query),
            normalize_search_limit(top_k),
            mode,
        )
        return json.dumps({"query": query, "results": results})
    except (ServiceUnavailableError, BulkheadRejectedError) as e:
        raise RuntimeError(f"Error: Database temporarily unavailable - {e.message}")
    except (PermissionError, ValueError, RuntimeError) as exc:
        raise ValueError(str(exc))


@mcp_server.tool(name="asila_get_document")
@circuit_breaker(name="postgresql", failure_threshold=5, recovery_timeout=30)
@bulkhead(name="postgresql_get_doc", max_concurrency=20)
async def get_document_content(document_id: str, ctx: Context | None = None) -> str:
    """
    Retrieve the full extracted text content and metadata of a specific document by its ID.
    
    Use this tool when a search result chunk indicates a relevant document and you need
    to read the entire surrounding context or the full file content.
    
    Args:
        document_id: The UUID of the document to retrieve (found in search results).
        
    Returns:
        JSON string containing the document id, title, status, and full extracted text.
        
    Errors:
        Raises an error string if the document is not found, or if the database is 
        temporarily unavailable (circuit breaker open).
    """
    if ctx is None:
        raise ValueError("MCP request context is required")
    principal = _principal_from_context(ctx)
    _require_any_scope(principal, "search:read", "knowledge:read", "documents:list", "mcp:discover")

    try:
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(principal.organization_id):
                    await set_transaction_organization(session, principal.organization_id)
                    result = await session.execute(
                        select(Document).where(Document.id == document_id)
                    )
                    document = result.scalar_one_or_none()
                    if document is None or document.status == DocumentStatus.DELETED:
                        raise ValueError("Document not found")
                    await record_audit_event(
                        session,
                        action="mcp.tool_call",
                        actor_id=principal.service_account_id or principal.user_id or principal.subject,
                        organization_id=principal.organization_id,
                        target_type="mcp_tool",
                        target_id="asila_get_document",
                        details={"document_id": document_id},
                    )
                    return json.dumps(
                        {
                            "id": document.id,
                            "title": document.title,
                            "source_uri": document.source_uri,
                            "status": document.status.value,
                            "content": document.extracted_text,
                        }
                    )
    except (ServiceUnavailableError, BulkheadRejectedError) as e:
        raise RuntimeError(f"Error: {e.message}")


def mcp_app():
    app = mcp_server.sse_app()
    app.add_middleware(MCPAuthMiddleware)
    return app
