from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import secrets
from sqlalchemy import select, text
from core.tenant.context import tenant_context
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import Tenant
from core.database.tenant_session import manager as tenant_session_manager

mcp_server = FastMCP("Asila")
import logging
logger = logging.getLogger(__name__)

async def verify_active_key(tenant_id: str, scope: str):
    from core.tenant.context import tenant_key_hash, tenant_ip
    
    current_hash = tenant_key_hash.get()
    current_ip = tenant_ip.get()

    # Enterprise Audit Logging
    logger.info(f"mcp_tool_execution | tenant_id={tenant_id} | tool={scope} | ip={current_ip}")

    if tenant_id == "ADMIN":
        return

    async with PlatformSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise Exception("API Key Revoked (Tenant not found)")
        
        if tenant.api_key_hash != current_hash:
            raise Exception("API Key Revoked (Hash mismatch). Please reconnect with new key.")
            
        if tenant.allowed_scopes and "*" not in tenant.allowed_scopes and scope not in tenant.allowed_scopes:
            raise Exception(f"Forbidden: API Key does not have the '{scope}' scope.")

def count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback approximation (1 token ≈ 4 characters)
        return len(text) // 4

@mcp_server.tool(name="asila_search_verified_docs")
async def search_verified_docs(query: Optional[str] = None, roles: Optional[list[str]] = None, top_k: int = 5) -> str:
    """
    Search across verified documents in the enterprise knowledge base. Provide roles to filter access.
    """
    if not query:
        return "Missing required argument: query. Please provide a search string."

    tenant_id = tenant_context.get()
    if not tenant_id or tenant_id == "ADMIN":
        return "Error: This tool requires a valid tenant context. Connect using a Tenant API Key."

    try:
        await verify_active_key(tenant_id, "search")
    except Exception as e:
        return str(e)

    # Cap top_k to a reasonable maximum to prevent oversized DB queries,
    # but the 2,500 token budget will be strictly enforced on the returned result list.
    if top_k > 50:
        top_k = 50

    try:
        from services.embeddings.service import generate_embeddings
        from domain.tenant.chunks.models import Chunk
        from domain.tenant.embeddings.models import Embedding
        from domain.tenant.documents.models import Document
        
        # 1. Generate query embedding
        query_vector = (await generate_embeddings([query]))[0]

        # 2. Open Tenant Session
        SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
        async with SessionMaker() as db:
            # 3. Vector Similarity Search
            stmt = select(Chunk, Document.title, Embedding.embedding.cosine_distance(query_vector).label('distance'))\
                .join(Embedding, Chunk.id == Embedding.chunk_id)\
                .join(Document, Chunk.document_id == Document.id)

            if roles:
                from sqlalchemy.dialects.postgresql import JSONB, array
                from sqlalchemy import cast, or_, func
                
                # allow if document has no roles (public), or if the JSONB array overlaps with the user's roles
                stmt = stmt.where(
                    or_(
                        Document.allowed_roles == None,
                        func.jsonb_array_length(cast(Document.allowed_roles, JSONB)) == 0,
                        cast(Document.allowed_roles, JSONB).has_any(array(roles))
                    )
                )
            
            stmt = stmt.order_by(text('distance ASC')).limit(top_k)
            
            result = await db.execute(stmt)
            rows = result.all()
            
            # Filter rows with poor relevance to prevent hallucination (e.g. negative tests)
            rows = [(c, t, d) for c, t, d in rows if d <= 0.25]

            if not rows:
                return "[]"

            output = []
            for chunk, title, distance in rows:
                candidate_item = {
                    "source": title,
                    "distance": distance,
                    "content": f"<document_content>{chunk.content}</document_content>"
                }
                # Check if adding this candidate item would exceed the 2,500 tokens budget
                temp_output = output + [candidate_item]
                if count_tokens(json.dumps(temp_output)) > 2500:
                    break
                output.append(candidate_item)
            
            return json.dumps(output)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Search error: {str(e)}", exc_info=True)
        return "### Error during search\nAn internal server error occurred while retrieving documents."

@mcp_server.tool(name="asila_get_ingestion_status")
async def get_ingestion_status(job_id: str) -> str:
    """
    Get the status of an ingestion job.
    """
    tenant_id = tenant_context.get()
    if not tenant_id or tenant_id == "ADMIN":
        return "Error: This tool requires a valid tenant context."
    
    try:
        await verify_active_key(tenant_id, "status")
    except Exception as e:
        return str(e)
    
    try:
        from domain.tenant.documents.models import FailedIngestion
        SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
        async with SessionMaker() as db:
            result = await db.execute(select(FailedIngestion).where(FailedIngestion.id == job_id))
            failed = result.scalar_one_or_none()
            if failed:
                return f"### Job Failed\\n**File**: {failed.file_name}\\n**Error**: {failed.error_message}\\n```\\n{failed.stack_trace}\\n```"
            
            return "Job is either pending, processing, or completed successfully. (ARQ job details not fully exposed)"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Status check error: {str(e)}", exc_info=True)
        return "An internal server error occurred while checking status."

@mcp_server.tool(name="asila_admin_create_tenant")
async def admin_create_tenant(name: str) -> str:
    """
    Create a new tenant in the platform (Admin only).
    """
    tenant_id = tenant_context.get()
    if tenant_id != "ADMIN":
        return "Error: This tool requires Platform Admin privileges. Connect using ASILA_MASTER_KEY."
    
    try:
        await verify_active_key(tenant_id, "admin")
    except Exception as e:
        return str(e)
    
    try:
        org_id = f"org_{uuid.uuid4().hex[:8]}"
        api_key = f"sk-asila-{secrets.token_urlsafe(32)}"
        
        async with PlatformSessionLocal() as db:
            tenant = Tenant(
                id=org_id,
                name=name,
                db_connection_string="postgresql+asyncpg://asila:asila@postgres:5432/asila_shared",
                api_key=api_key
            )
            db.add(tenant)
            await db.commit()
            
        return f"### Tenant Created successfully!\\n**ID**: {org_id}\\n**Name**: {name}\\n**API Key**: `{api_key}`\\n\\n*(Save this API Key, it will not be shown again)*"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Tenant creation error: {str(e)}", exc_info=True)
        return "An internal server error occurred while creating tenant."

@mcp_server.tool(name="asila_admin_rotate_key")
async def admin_rotate_key(tenant_id: str) -> str:
    """
    Rotate the API key for a given tenant (Admin only).
    """
    ctx_tenant = tenant_context.get()
    if ctx_tenant != "ADMIN":
        return "Error: This tool requires Platform Admin privileges."
    
    try:
        await verify_active_key(ctx_tenant, "admin")
    except Exception as e:
        return str(e)
    
    try:
        new_api_key = f"sk-asila-{secrets.token_urlsafe(32)}"
        async with PlatformSessionLocal() as db:
            result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = result.scalar_one_or_none()
            if not tenant:
                return f"Error: Tenant {tenant_id} not found."
            
            tenant.api_key = new_api_key
            await db.commit()
            
        return f"### API Key Rotated\\n**Tenant ID**: {tenant_id}\\n**New API Key**: `{new_api_key}`"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Key rotation error: {str(e)}", exc_info=True)
        return "An internal server error occurred while rotating key."
