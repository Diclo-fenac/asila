from core.config.settings import Settings
from services.ai.factory import build_embedding_provider


def test_provider_factory_defaults_to_ollama():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://localhost/asila",
        REDIS_URL="redis://localhost:6379/0",
        POSTGRES_PASSWORD="test",
        AI_PROVIDER="ollama",
    )

    provider = build_embedding_provider(settings)

    assert provider.__class__.__name__ == "OllamaEmbeddingProvider"

