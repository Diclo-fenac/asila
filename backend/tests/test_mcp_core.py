from api.routes.mcp_core import mcp_server
import pytest


@pytest.mark.asyncio
async def test_mcp_exposes_read_tools_without_administration():
    names = {tool.name for tool in await mcp_server.list_tools()}

    assert {
        "asila_list_repositories",
        "asila_search",
        "asila_get_document",
    } <= names
    assert "asila_admin_create_tenant" not in names
    assert "asila_admin_rotate_key" not in names


@pytest.mark.asyncio
async def test_mcp_search_supports_explicit_hybrid_mode():
    tool = next(tool for tool in await mcp_server.list_tools() if tool.name == "asila_search")
    assert tool.inputSchema["properties"]["mode"]["enum"] == ["keyword", "hybrid"]
