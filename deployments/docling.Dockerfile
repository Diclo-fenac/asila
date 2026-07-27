FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn python-multipart httpx
COPY ../backend/scripts/mock_docling.py /app/mock_docling.py
EXPOSE 5001
CMD ["python", "mock_docling.py"]
