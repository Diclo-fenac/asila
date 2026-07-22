import httpx
import pytest

from api.main import app


@pytest.mark.asyncio
async def test_health_endpoint_is_available_without_authentication():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://asila") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_exposes_core_routes_and_not_retired_tenant_routes():
    paths = app.openapi()["paths"]

    assert "/api/v1/knowledge/retrieval/search" in paths
    assert "/api/v1/health/ready" in paths
    assert "/api/v1/knowledge/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/api-keys" in paths
    assert "/api/v1/tenants/register" not in paths
    assert "/api/v1/ingest" not in paths
