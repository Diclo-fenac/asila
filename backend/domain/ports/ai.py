from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class GenerationProvider(Protocol):
    model: str

    async def generate(self, prompt: str, context: str = "") -> str: ...
