import google.generativeai as genai
from core.config.settings import settings
from typing import List
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.embedding_model = settings.EMBEDDING_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_response(self, prompt: str, context: str = "") -> str:
        full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        response = self.model.generate_content(full_prompt)
        return response.text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_document_content(self, file_path: str, mime_type: str = None) -> str:
        """
        Uploads a file (PDF, Image) to Gemini and extracts its content as structured Markdown.
        """
        # Upload the file to Gemini's File API
        uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
        
        # Wait briefly for processing if it's a large PDF
        while uploaded_file.state.name == 'PROCESSING':
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        prompt = (
            "Transcribe this document exactly into clean Markdown. "
            "Preserve all headings, paragraphs, lists, and tables. "
            "Extract any text from images or diagrams. "
            "Do not add any conversational filler, just return the document content."
        )
        
        response = self.model.generate_content([uploaded_file, prompt])
        
        # Cleanup file from Google's servers
        genai.delete_file(uploaded_file.name)
        
        return response.text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_embedding(self, text: str) -> List[float]:
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        result = genai.embed_content(
            model=self.embedding_model,
            content=texts,
            task_type="retrieval_document"
        )
        return result['embedding']

gemini_service = GeminiService()
