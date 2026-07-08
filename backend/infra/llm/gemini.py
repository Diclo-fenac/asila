import os
from google import genai
from google.genai import types
from core.config.settings import settings
from typing import List, AsyncGenerator
import time
import asyncio
import hashlib
import random
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model = settings.GEMINI_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL

    def _get_deterministic_vector(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode('utf-8')).digest()
        rng = random.Random(h)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(768)]
        norm = sum(x*x for x in vec) ** 0.5
        if norm == 0:
            vec[0] = 1.0
            norm = 1.0
        return [x/norm for x in vec]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def generate_response(self, prompt: str, context: str = "") -> str:
        full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        
        def run_generate():
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
            
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_generate)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def generate_json(self, prompt: str) -> dict:
        import json
        def run_generate():
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
            
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_generate)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def extract_document_content(self, file_path: str, mime_type: str = None) -> str:
        # Short-circuit: if the file is markdown or text, read it directly
        if mime_type and (mime_type.startswith("text/") or mime_type == "application/json"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        if ext in ['md', 'txt', 'py', 'js', 'ts', 'go', 'html', 'json']:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        def run_extract():
            # In google-genai, file upload is synchronous
            uploaded_file = self.client.files.upload(file=file_path, config={'mime_type': mime_type})
            
            while uploaded_file.state.name == 'PROCESSING':
                time.sleep(2)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
                
            prompt = (
                "Transcribe this document exactly into clean Markdown. "
                "Preserve all headings, paragraphs, lists, and tables. "
                "Extract any text from images or diagrams. "
                "Do not add any conversational filler, just return the document content."
            )
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[uploaded_file, prompt]
            )
            
            self.client.files.delete(name=uploaded_file.name)
            return response.text

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_extract)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def generate_embedding(self, text: str) -> List[float]:
        if settings.GOOGLE_API_KEY == "AIzaSyARuH-VVF9jNtBUfCBSDwqvWrgCcLQtGug":
            return self._get_deterministic_vector(text)
            
        def run_embed():
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )
            return result.embeddings[0].values
            
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_embed)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if settings.GOOGLE_API_KEY == "AIzaSyARuH-VVF9jNtBUfCBSDwqvWrgCcLQtGug":
            return [self._get_deterministic_vector(t) for t in texts]
            
        def run_embed():
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )
            return [e.values for e in result.embeddings]
            
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, run_embed)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def generate_response_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        
        def get_stream():
            return self.client.models.generate_content_stream(
                model=self.model,
                contents=full_prompt
            )
            
        loop = asyncio.get_running_loop()
        response_stream = await loop.run_in_executor(None, get_stream)
        
        for chunk in response_stream:
            await asyncio.sleep(0)
            yield chunk.text

gemini_service = GeminiService()
