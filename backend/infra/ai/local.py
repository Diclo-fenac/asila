from collections.abc import Sequence

import httpx


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = client

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=60)
        try:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": list(texts)},
            )
            response.raise_for_status()
            embeddings = response.json().get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise RuntimeError("Ollama returned an invalid embedding response")
            return embeddings
        finally:
            if owns_client:
                await client.aclose()


class OllamaGenerationProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = client

    async def generate(self, prompt: str, context: str = "") -> str:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=120)
        try:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer only from the supplied context. Say you do not know when it is insufficient.",
                        },
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json().get("message", {}).get("content")
            if not isinstance(content, str):
                raise RuntimeError("Ollama returned an invalid generation response")
            return content
        finally:
            if owns_client:
                await client.aclose()
