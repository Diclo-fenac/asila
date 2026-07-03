import asyncio
from arq.connections import RedisSettings
from core.config.settings import settings
from core.database.tenant_session import manager as tenant_session_manager
from services.ingestion.service import process_document
from typing import Optional, Dict, BinaryIO
import io

async def process_document_task(
    ctx, 
    tenant_id: str, 
    title: str, 
    content: Optional[str] = None, 
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    source_url: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Background task to process a document.
    """
    # Create a session for this tenant
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    
    async with SessionMaker() as db:
        file_data = io.BytesIO(file_bytes) if file_bytes else None
        
        await process_document(
            db=db,
            tenant_id=tenant_id,
            title=title,
            content=content,
            file_data=file_data,
            file_name=file_name,
            mime_type=mime_type,
            source_url=source_url,
            metadata=metadata
        )

class WorkerSettings:
    functions = [process_document_task]
    
    from urllib.parse import urlparse
    url = urlparse(settings.REDIS_URL)
    
    redis_settings = RedisSettings(
        host=url.hostname or 'localhost',
        port=url.port or 6379,
        database=int(url.path.lstrip('/') or 0)
    )
