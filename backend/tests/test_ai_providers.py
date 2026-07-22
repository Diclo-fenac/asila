import httpx
import pytest

from infra.ai.local import OllamaEmbeddingProvider, OllamaGenerationProvider
from infra.ai.gemini import GeminiEmbeddingProvider


@pytest.mark.asyncio
async def test_ollama_embedding_provider_maps_embeddings():
    async def handler(request: httpx.Request):
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    provider = OllamaEmbeddingProvider(
        base_url="http://ollama",
        model="nomic-embed-text",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await provider.embed(["hello"]) == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_ollama_generation_provider_returns_message_content():
    async def handler(request: httpx.Request):
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={"message": {"content": "grounded answer"}},
        )

    provider = OllamaGenerationProvider(
        base_url="http://ollama",
        model="llama3.2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await provider.generate("question", "context") == "grounded answer"


@pytest.mark.asyncio
async def test_gemini_embedding_provider_maps_values():
    class Models:
        def embed_content(self, **_kwargs):
            return type("Response", (), {"embeddings": [type("Embedding", (), {"values": [0.1, 0.2]})()]})()

    client = type("Client", (), {"models": Models()})()
    provider = GeminiEmbeddingProvider(api_key="test", model="embedding", client=client)

    assert await provider.embed(["hello"]) == [[0.1, 0.2]]
