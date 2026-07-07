import asyncio
import json
import time
try:
    import pytest
except ImportError:
    class DummyPytest:
        class DummyMark:
            @staticmethod
            def asyncio(func):
                return func
        mark = DummyMark()
    pytest = DummyPytest()

import httpx
from typing import Dict, Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from sqlalchemy import select, text
from core.database.platform_session import PlatformSessionLocal
from core.database.tenant_session import manager as tenant_session_manager
from domain.platform.tenants.models import Tenant

BASE_URL = "http://localhost:8000"
SSE_URL = f"{BASE_URL}/mcp/sse"

async def register_tenant(client: httpx.AsyncClient, name: str, email: str) -> Dict[str, str]:
    """Register a new tenant via the API and return the tenant_id and api_key."""
    response = await client.post(
        f"{BASE_URL}/api/v1/tenants/register",
        json={"name": name, "email": email}
    )
    assert response.status_code == 201, f"Failed to register tenant: {response.text}"
    data = response.json()
    assert "tenant_id" in data
    assert "api_key" in data
    return data

async def upload_doc(client: httpx.AsyncClient, api_key: str, title: str, content: str) -> str:
    """Trigger background document ingestion for a tenant and return the job_id."""
    # Use multipart form format as expected by /api/v1/ingest
    data = {
        "title": title,
        "content": content
    }
    headers = {
        "asila-api-key": api_key
    }
    response = await client.post(
        f"{BASE_URL}/api/v1/ingest",
        headers=headers,
        data=data
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    job_data = response.json()
    assert job_data.get("status") == "queued"
    return job_data.get("job_id")

async def poll_task_completion(client: httpx.AsyncClient, api_key: str, job_id: str, timeout: float = 40.0) -> Dict[str, Any]:
    """Poll task status endpoint until job is completed or failed."""
    start_time = time.time()
    headers = {"asila-api-key": api_key}
    while time.time() - start_time < timeout:
        response = await client.get(
            f"{BASE_URL}/api/v1/tasks/{job_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get task status: {response.text}"
        data = response.json()
        status = data.get("status")
        if status in ("completed", "failed"):
            return data
        await asyncio.sleep(1.0)
    raise TimeoutError(f"Task {job_id} did not complete within {timeout} seconds.")

async def run_mcp_search(api_key: str, query: str) -> str:
    """Connect to FastMCP SSE endpoint and execute aasila_search_verified_docs tool."""
    async with sse_client(SSE_URL, headers={"asila-api-key": api_key}) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Wait for server initialization
            await asyncio.sleep(0.1)
            result = await session.call_tool("aasila_search_verified_docs", {"query": query, "top_k": 3})
            return result.content[0].text

@pytest.mark.asyncio
async def test_multi_tenant_isolation_under_concurrency():
    async with httpx.AsyncClient() as client:
        # Create unique tenant names to ensure clean test runs
        suffix = str(int(time.time()))
        tenant_a_name = f"ConcurTenantA_{suffix}"
        tenant_b_name = f"ConcurTenantB_{suffix}"

        print(f"\n[SETUP] Registering Tenant A ({tenant_a_name}) and Tenant B ({tenant_b_name})...")
        tenant_a = await register_tenant(client, tenant_a_name, "admin_a@concur.com")
        tenant_b = await register_tenant(client, tenant_b_name, "admin_b@concur.com")

        tenant_id_a, api_key_a = tenant_a["tenant_id"], tenant_a["api_key"]
        tenant_id_b, api_key_b = tenant_b["tenant_id"], tenant_b["api_key"]

        # Ensure database schemas are created
        # The register endpoint calls create_tenant_service which automatically creates schemas.
        # Let's verify schema exists for both tenants.
        async with PlatformSessionLocal() as session:
            result_a = await session.execute(select(Tenant).where(Tenant.id == tenant_id_a))
            assert result_a.scalar_one_or_none() is not None, "Tenant A not found in platform DB"
            result_b = await session.execute(select(Tenant).where(Tenant.id == tenant_id_b))
            assert result_b.scalar_one_or_none() is not None, "Tenant B not found in platform DB"

        # -------------------------------------------------------------
        # STEP 7.1 — Simultaneous Ingestion
        # -------------------------------------------------------------
        print("\n[STEP 7.1] Triggering simultaneous document ingestion...")
        doc_a_title = "Document A - Security Guidelines"
        doc_a_content = "This is secret document A for Tenant A. Codephrase: alpha_concur_2026. Keep it isolated."

        doc_b_title = "Document B - Operational Playbook"
        doc_b_content = "This is secret document B for Tenant B. Codephrase: beta_concur_2026. Strictly confidential."

        # Fire both upload requests in parallel
        task_a_fut = upload_doc(client, api_key_a, doc_a_title, doc_a_content)
        task_b_fut = upload_doc(client, api_key_b, doc_b_title, doc_b_content)
        job_id_a, job_id_b = await asyncio.gather(task_a_fut, task_b_fut)

        print(f"Tenant A job ID: {job_id_a}")
        print(f"Tenant B job ID: {job_id_b}")

        # Poll tasks in parallel until complete
        poll_a_fut = poll_task_completion(client, api_key_a, job_id_a)
        poll_b_fut = poll_task_completion(client, api_key_b, job_id_b)
        res_a, res_b = await asyncio.gather(poll_a_fut, poll_b_fut)

        assert res_a["status"] == "completed", f"Ingestion for Tenant A failed: {res_a}"
        assert res_b["status"] == "completed", f"Ingestion for Tenant B failed: {res_b}"
        print("Ingestions completed successfully.")

        # Verify database isolation: check documents table in schemas
        # Using separate connection makers to check
        SessionMakerA = await tenant_session_manager.get_tenant_sessionmaker(tenant_id_a)
        SessionMakerB = await tenant_session_manager.get_tenant_sessionmaker(tenant_id_b)

        # Override URL for local testing from host
        SessionMakerA.kw["bind"].url = SessionMakerA.kw["bind"].url.set(host="localhost")
        SessionMakerB.kw["bind"].url = SessionMakerB.kw["bind"].url.set(host="localhost")

        async with SessionMakerA() as db_a:
            docs_a = (await db_a.execute(text("SELECT title FROM documents"))).scalars().all()
            print(f"Tenant A docs in DB: {docs_a}")
            assert len(docs_a) == 1
            assert docs_a[0] == doc_a_title

        async with SessionMakerB() as db_b:
            docs_b = (await db_b.execute(text("SELECT title FROM documents"))).scalars().all()
            print(f"Tenant B docs in DB: {docs_b}")
            assert len(docs_b) == 1
            assert docs_b[0] == doc_b_title

        print("-> PASS: Simultaneous ingestion succeeded with perfect database-level isolation (no cross-contamination).")

        # -------------------------------------------------------------
        # STEP 7.2 — Simultaneous Search
        # -------------------------------------------------------------
        print("\n[STEP 7.2] Performing simultaneous search queries...")

        start_search_time = time.time()
        
        query_a = f"Source: {doc_a_title}\n\n{doc_a_content}"
        query_b = f"Source: {doc_b_title}\n\n{doc_b_content}"
        # Fire parallel search requests via MCP
        search_a_fut = run_mcp_search(api_key_a, query_a)
        search_b_fut = run_mcp_search(api_key_b, query_b)
        
        search_res_a, search_res_b = await asyncio.gather(search_a_fut, search_b_fut)
        
        duration = time.time() - start_search_time
        print(f"Parallel search completed in {duration:.4f} seconds.")

        # Verify only own tenant's data returned
        print(f"Tenant A search result: {search_res_a}")
        print(f"Tenant B search result: {search_res_b}")

        assert "alpha_concur_2026" in search_res_a
        assert "beta_concur_2026" not in search_res_a

        assert "beta_concur_2026" in search_res_b
        assert "alpha_concur_2026" not in search_res_b

        # Verify both complete within 2s
        # Note: Since they ran in parallel, the total elapsed time for both should be < 2.0s.
        assert duration < 2.0, f"Parallel searches took {duration:.2f}s, which is slower than the 2s requirement."

        print("-> PASS: Parallel searches returned strictly isolated tenant data and completed in < 2 seconds.")

        # -------------------------------------------------------------
        # STEP 7.3 — Schema Migration Isolation
        # -------------------------------------------------------------
        print("\n[STEP 7.3] Triggering schema migration during in-flight search...")

        # Concurrently execute a search query and a tenant schema migration
        search_task = asyncio.create_task(run_mcp_search(api_key_a, query_a))
        from core.config.settings import settings
        db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/asila_platform"
        migration_task = asyncio.create_task(tenant_session_manager.create_tenant_schema(tenant_id_a, db_url))

        search_res, _ = await asyncio.gather(search_task, migration_task)

        print(f"In-flight search result: {search_res}")
        assert "alpha_concur_2026" in search_res
        print("In-flight search completed successfully without error during active migration.")

        # Verify that the schema was not corrupted and documents are still readable
        async with SessionMakerA() as db_a:
            docs_a_post = (await db_a.execute(text("SELECT title FROM documents"))).scalars().all()
            assert len(docs_a_post) == 1
            assert docs_a_post[0] == doc_a_title
            
        print("-> PASS: Schema migration executed cleanly in-flight with no search disruption or schema corruption.")
        print("\n[SUCCESS] All multi-tenant isolation concurrency verification steps passed!")

if __name__ == "__main__":
    asyncio.run(test_multi_tenant_isolation_under_concurrency())
