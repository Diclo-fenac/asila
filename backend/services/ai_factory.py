from core.config.settings import Settings, settings as runtime_settings
from core.security.secret_box import decrypt_secret
from domain.platform.provider_credentials.models import ProviderCredential
from infra.ai.gemini import GeminiEmbeddingProvider, GeminiGenerationProvider
from infra.ai.local import OllamaEmbeddingProvider, OllamaGenerationProvider
from infra.ai.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleGenerationProvider,
)


def _provider_config(config: Settings, credential: ProviderCredential | None):
    provider = credential.provider if credential is not None else config.AI_PROVIDER
    endpoint = credential.endpoint if credential is not None else None
    embedding_model = credential.embedding_model if credential is not None else None
    generation_model = credential.generation_model if credential is not None else None
    api_key = None
    if credential is not None and credential.encrypted_api_key:
        api_key = decrypt_secret(credential.encrypted_api_key, config.ASILA_MASTER_KEY)
    return provider, endpoint, embedding_model, generation_model, api_key


def build_embedding_provider(
    config: Settings = runtime_settings,
    credential: ProviderCredential | None = None,
):
    provider, endpoint, embedding_model, _, api_key = _provider_config(config, credential)
    if provider == "ollama":
        return OllamaEmbeddingProvider(
            base_url=endpoint or config.OLLAMA_BASE_URL,
            model=embedding_model or config.OLLAMA_EMBEDDING_MODEL,
        )
    if provider == "openai-compatible":
        if not (endpoint or config.OPENAI_BASE_URL) or not (api_key or config.OPENAI_API_KEY):
            raise ValueError("OpenAI-compatible provider requires base URL and API key")
        return OpenAICompatibleEmbeddingProvider(
            base_url=endpoint or config.OPENAI_BASE_URL,
            model=embedding_model or config.OPENAI_EMBEDDING_MODEL,
            api_key=api_key or config.OPENAI_API_KEY,
        )
    if provider == "gemini":
        if not (api_key or config.GOOGLE_API_KEY):
            raise ValueError("Gemini provider requires an API key")
        return GeminiEmbeddingProvider(
            api_key=api_key or config.GOOGLE_API_KEY,
            model=embedding_model or config.EMBEDDING_MODEL,
        )
    raise ValueError(f"Unsupported embedding provider: {provider}")


def build_generation_provider(
    config: Settings = runtime_settings,
    credential: ProviderCredential | None = None,
):
    provider, endpoint, _, generation_model, api_key = _provider_config(config, credential)
    if provider == "ollama":
        return OllamaGenerationProvider(
            base_url=endpoint or config.OLLAMA_BASE_URL,
            model=generation_model or config.OLLAMA_GENERATION_MODEL,
        )
    if provider == "openai-compatible":
        if not (endpoint or config.OPENAI_BASE_URL) or not (api_key or config.OPENAI_API_KEY):
            raise ValueError("OpenAI-compatible provider requires base URL and API key")
        return OpenAICompatibleGenerationProvider(
            base_url=endpoint or config.OPENAI_BASE_URL,
            model=generation_model or config.OPENAI_GENERATION_MODEL,
            api_key=api_key or config.OPENAI_API_KEY,
        )
    if provider == "gemini":
        if not (api_key or config.GOOGLE_API_KEY):
            raise ValueError("Gemini provider requires an API key")
        return GeminiGenerationProvider(
            api_key=api_key or config.GOOGLE_API_KEY,
            model=generation_model or config.GEMINI_MODEL,
        )
    raise ValueError(f"Unsupported generation provider: {provider}")


async def _organization_credential(organization_id: str) -> ProviderCredential | None:
    from sqlalchemy import select

    from core.database.platform_session import PlatformSessionLocal

    async with PlatformSessionLocal() as session:
        result = await session.execute(
            select(ProviderCredential)
            .where(
                ProviderCredential.organization_id == organization_id,
                ProviderCredential.is_enabled.is_(True),
            )
            .order_by(ProviderCredential.created_at.asc())
        )
        return result.scalars().first()


async def build_organization_embedding_provider(organization_id: str):
    return build_embedding_provider(credential=await _organization_credential(organization_id))


async def build_organization_generation_provider(organization_id: str):
    return build_generation_provider(credential=await _organization_credential(organization_id))
