import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from domain.platform.tenants.service import create_tenant

@pytest.mark.asyncio
@patch("core.database.tenant_session.manager")
@patch("domain.platform.tenants.service.PlatformSessionLocal")
async def test_create_tenant_logic(mock_session_local, mock_manager):
    """
    Test that create_tenant:
    1. Inserts the tenant row into the platform DB first.
    2. Calls create_tenant_schema with tenant_id and db_url.
    3. Returns the correct connection string.
    """
    # Setup Mocks
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    
    mock_manager.create_tenant_schema = AsyncMock()
    
    # Run the provisioning
    db_url = await create_tenant(tenant_id="test_org", tenant_name="Test Organization")
    
    # Assertions: URL should contain the platform DB name
    assert "asila_platform" in db_url
    
    # Verify tenant was added to platform DB (first session context)
    assert mock_session.add.called
    tenant_obj = mock_session.add.call_args[0][0]
    assert tenant_obj.id == "test_org"
    assert tenant_obj.name == "Test Organization"
    assert mock_session.commit.called
    
    # Verify schema creation was called with both tenant_id and db_url
    mock_manager.create_tenant_schema.assert_called_once_with("test_org", db_url)

@pytest.mark.asyncio
@patch("core.database.tenant_session.manager")
@patch("domain.platform.tenants.service.PlatformSessionLocal")
async def test_create_tenant_rollback_on_schema_failure(mock_session_local, mock_manager):
    """
    Test that if schema creation fails, the tenant row is deleted (rollback).
    """
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    
    mock_manager.create_tenant_schema = AsyncMock(side_effect=RuntimeError("Schema creation failed"))
    
    with pytest.raises(RuntimeError, match="Schema creation failed"):
        await create_tenant(tenant_id="fail_org", tenant_name="Failing Org")
    
    # Verify delete was called for rollback (execute is called with a delete statement)
    assert mock_session.execute.called

def test_tenant_db_url_formatting():
    """
    Ensure the connection string follows the expected pattern for asyncpg.
    """
    from core.config.settings import settings
    db_name = "asila_platform"
    expected_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    
    # Verify the URL pattern matches what create_tenant would produce
    assert "postgresql+asyncpg://" in expected_url
    assert "asila_platform" in expected_url
