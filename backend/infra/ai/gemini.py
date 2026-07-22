import asyncio
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types


async def _run_sync(function):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="asila-gemini") as executor:
        return await loop.run_in_executor(executor, function)


class GeminiEmbeddingProvider:
    def __init__(self, *, api_key: str, model: str, client=None):
        self.model = model
        self._client = client or genai.Client(api_key=api_key)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        values = list(texts)

        def run():
            response = self._client.models.embed_content(
                model=self.model,
                contents=values,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return [list(item.values) for item in response.embeddings]

        result = await _run_sync(run)
        if len(result) != len(values):
            raise RuntimeError("Gemini returned an invalid embedding response")
        return result


class GeminiGenerationProvider:
    def __init__(self, *, api_key: str, model: str, client=None):
        self.model = model
        self._client = client or genai.Client(api_key=api_key)

    async def generate(self, prompt: str, context: str = "") -> str:
        def run():
            response = self._client.models.generate_content(
                model=self.model,
                contents=(
                    "Use only the supplied context. Say you do not know when it is insufficient.\n\n"
                    f"Context:\n{context}\n\nQuestion:\n{prompt}"
                ),
            )
            return response.text

        result = await _run_sync(run)
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Gemini returned an invalid generation response")
        return result
