import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock
from workers.main import process_document_task
from domain.tenant.documents.models import FailedIngestion
from sqlalchemy import select
from core.database.tenant_session import manager
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import Tenant

@pytest.mark.asyncio
async def test_worker_catches_cancelled_error_and_writes_dlq():
    """
    Ensure that if a background worker receives a SIGTERM or is aborted via ARQ (which raises asyncio.CancelledError),
    it successfully catches the BaseException and writes a FailedIngestion record.
    """
    tenant_id = f"test_resilience_{uuid.uuid4().hex[:8]}"
    
    # 1. Create a dummy tenant so the tenant schema exists
    async with PlatformSessionLocal() as db:
        db.add(Tenant(
            id=tenant_id,
            name="Test Resilience Tenant",
            db_connection_string="postgresql+asyncpg://asila:asila@postgres:5432/asila_platform",
            status="ACTIVE"
        ))
        await db.commit()
        
    # Create schema for the tenant
    from core.config.settings import settings
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/asila_platform"
    await manager.create_tenant_schema(tenant_id, db_url)
    
    ctx = {"job_id": f"job_{uuid.uuid4().hex}"}
    
    # 2. Mock process_document to raise CancelledError (simulating a timeout/abort)
    with patch("workers.main.process_document", new_callable=AsyncMock) as mock_process:
        mock_process.side_effect = asyncio.CancelledError("Job was cancelled by ARQ timeout")
        
        # 3. Call the task
        with pytest.raises(asyncio.CancelledError):
            await process_document_task(
                ctx=ctx,
                tenant_id=tenant_id,
                title="Hanging Document",
                content="This document will hang."
            )
            
    # 4. Verify that FailedIngestion was created
    SessionMaker = await manager.get_tenant_sessionmaker(tenant_id)
    async with SessionMaker() as db:
        result = await db.execute(select(FailedIngestion).where(FailedIngestion.tenant_id == tenant_id))
        failed_record = result.scalar_one_or_none()
        
        assert failed_record is not None, "FailedIngestion record was not created!"
        assert "CancelledError" in failed_record.error_message
        assert failed_record.file_name == "Hanging Document"
