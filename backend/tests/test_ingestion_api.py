import pytest
import httpx
import asyncio
import uuid
from typing import Dict, Any

# We assume the docker-compose backend is running on http://localhost:8000
BASE_URL = "http://localhost:8000"

async def register_tenant(client: httpx.AsyncClient, name: str, email: str) -> str:
    response = await client.post(f"{BASE_URL}/api/v1/tenants/register", json={
        "name": name,
        "email": email
    })
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return response.json()["api_key"]

@pytest.mark.asyncio
async def test_upload_oversized_file_rejected():
    """
    Ensure the 10MB file limit is enforced at the router layer.
    """
    async with httpx.AsyncClient() as client:
        # Create a tenant for auth
        unique_id = uuid.uuid4().hex[:8]
        api_key = await register_tenant(client, f"Oversized Test Tenant {unique_id}", f"oversized_{unique_id}@example.com")
        
        # Create a dummy payload that exceeds 10MB (11MB)
        # Using a very large string to simulate file bytes
        large_file_content = b"A" * (11 * 1024 * 1024)
        
        files = {
            "file": ("massive.pdf", large_file_content, "application/pdf")
        }
        data = {
            "title": "Massive Document"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/ingest",
            headers={"asila-api-key": api_key},
            data=data,
            files=files,
            timeout=10.0
        )
        
        assert response.status_code == 413
        assert "10MB" in response.text

@pytest.mark.asyncio
async def test_upload_spoofed_mime_type_rejected():
    """
    Ensure python-magic catches files where the extension doesn't match the true cryptographic magic numbers.
    """
    async with httpx.AsyncClient() as client:
        unique_id = uuid.uuid4().hex[:8]
        api_key = await register_tenant(client, f"Spoof Test Tenant {unique_id}", f"spoof_{unique_id}@example.com")
        
        # A mock Windows Executable MZ header spoofed as a PDF
        spoofed_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
        
        files = {
            "file": ("innocent.pdf", spoofed_content, "application/pdf")
        }
        data = {
            "title": "Spoofed Document"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/ingest",
            headers={"asila-api-key": api_key},
            data=data,
            files=files
        )
        
        assert response.status_code == 400
        assert "Invalid file content" in response.text
