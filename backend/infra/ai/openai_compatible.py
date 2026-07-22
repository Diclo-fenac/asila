from collections.abc import Sequence

import httpx


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = client

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=60)
        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": list(texts)},
            )
            response.raise_for_status()
            data = response.json().get("data")
            if not isinstance(data, list) or len(data) != len(texts):
                raise RuntimeError("Embedding provider returned an invalid response")
            return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        finally:
            if owns_client:
                await client.aclose()


class OpenAICompatibleGenerationProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = client

    async def generate(self, prompt: str, context: str = "") -> str:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=120)
        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Use only supplied context."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise RuntimeError("Generation provider returned an invalid response")
            return content
        finally:
            if owns_client:
                await client.aclose()
