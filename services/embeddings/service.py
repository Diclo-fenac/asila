from infra.llm.gemini import gemini_service
from typing import List

async def generate_embedding(text: str) -> List[float]:
    return await gemini_service.generate_embedding(text)

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    return await gemini_service.generate_embeddings(texts)
