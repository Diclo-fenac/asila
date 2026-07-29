from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.security.secret_box import encrypt_secret
from domain.platform.provider_credentials.models import ProviderCredential


SUPPORTED_PROVIDERS = {"ollama", "openai-compatible", "gemini"}


async def upsert_provider_credential(
    session: AsyncSession,
    *,
    organization_id: str,
    provider: str,
    endpoint: str | None,
    embedding_model: str | None,
    generation_model: str | None,
    api_key: str | None,
    enabled: bool,
) -> ProviderCredential:
    provider = provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    if provider != "ollama" and api_key and not settings.ASILA_MASTER_KEY:
        raise ValueError("ASILA_MASTER_KEY is required for cloud provider credentials")
    result = await session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == organization_id,
        )
    )
    credentials = list(result.scalars().all())
    credential = next((item for item in credentials if item.provider == provider), None)
    if provider != "ollama" and credential is None and not api_key:
        raise ValueError("A provider API key is required")
    if credential is None:
        credential = ProviderCredential(
            id=f"pc_{uuid4().hex}",
            organization_id=organization_id,
            provider=provider,
        )
        session.add(credential)
        credentials.append(credential)
    if enabled:
        for item in credentials:
            if item is not credential:
                item.is_enabled = False
    credential.endpoint = endpoint
    credential.embedding_model = embedding_model
    credential.generation_model = generation_model
    credential.encrypted_api_key = (
        encrypt_secret(api_key, settings.ASILA_MASTER_KEY) if api_key else credential.encrypted_api_key
    )
    credential.is_enabled = enabled
    await session.flush()
    return credential
