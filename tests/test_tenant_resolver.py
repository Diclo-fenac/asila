import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.tenant.resolver import resolve_tenant
from fastapi import HTTPException

@pytest.mark.asyncio
@patch("core.tenant.resolver.redis_client")
@patch("core.tenant.resolver.PlatformSessionLocal")
async def test_resolve_tenant_cached(mock_session, mock_redis):
    """
    Test that the resolver uses Redis cache if available (performance optimization).
    """
    mock_redis.get = AsyncMock(return_value=b"postgresql+asyncpg://cached_db")
    
    db_url = await resolve_tenant("test_org")
    
    assert db_url == "postgresql+asyncpg://cached_db"
    assert not mock_session.called # Should not hit DB

@pytest.mark.asyncio
@patch("core.tenant.resolver.redis_client")
@patch("core.tenant.resolver.PlatformSessionLocal")
async def test_resolve_tenant_db_fallback(mock_session_local, mock_redis):
    """
    Test that the resolver falls back to the DB and updates the cache if not in Redis.
    """
    mock_redis.get = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_tenant = MagicMock()
    mock_tenant.db_connection_string = "postgresql+asyncpg://db_from_sql"
    mock_tenant.is_active = True
    
    mock_result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = mock_result
    mock_session_local.return_value.__aenter__.return_value = mock_session
    
    db_url = await resolve_tenant("db_org")
    
    assert db_url == "postgresql+asyncpg://db_from_sql"
    assert mock_redis.setex.called
    assert mock_redis.setex.call_args[0][0] == "tenant:db_org:db"

@pytest.mark.asyncio
@patch("core.tenant.resolver.redis_client")
@patch("core.tenant.resolver.PlatformSessionLocal")
async def test_resolve_tenant_invalid(mock_session_local, mock_redis):
    """
    Test that the resolver raises 403 for non-existent or inactive tenants.
    """
    mock_redis.get = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # Tenant not found
    
    mock_session.execute.return_value = mock_result
    mock_session_local.return_value.__aenter__.return_value = mock_session
    
    with pytest.raises(HTTPException) as excinfo:
        await resolve_tenant("fake_org")
    
    assert excinfo.value.status_code == 403
