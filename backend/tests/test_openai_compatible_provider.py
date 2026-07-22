import httpx
import pytest

from infra.ai.openai_compatible import OpenAICompatibleEmbeddingProvider


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider():
    async def handler(request: httpx.Request):
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.3]}]})

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://provider/v1",
        model="local-embed",
        api_key="test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await provider.embed(["hello"]) == [[0.3]]

