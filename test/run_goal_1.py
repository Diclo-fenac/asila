import asyncio
import httpx

async def main():
    master_key = "sk-asila-master-key-12345"
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create OrgAlpha
        print("Creating OrgAlpha...")
        r = await client.post(f"{base_url}/api/v1/tenants/register", headers={"asila-api-key": master_key}, json={"name": "OrgAlpha"})
        alpha_key = r.json().get("api_key")
        
        # 1. Create OrgBeta
        print("Creating OrgBeta...")
        r = await client.post(f"{base_url}/api/v1/tenants/register", headers={"asila-api-key": master_key}, json={"name": "OrgBeta"})
        beta_key = r.json().get("api_key")
        
        # 2. Upload to Tenant A
        print("Uploading to OrgAlpha...")
        files = {"file": ("secret.txt", b"PROJECT-NIGHTHAWK-CONFIDENTIAL", "text/plain")}
        r = await client.post(f"{base_url}/api/v1/documents/upload", headers={"asila-api-key": alpha_key}, files=files)
        print("Upload status:", r.status_code)
        
        # Wait a moment for ingestion to finish
        print("Waiting for ingestion...")
        await asyncio.sleep(5)
        
        # 3. Search using Tenant B's key
        print("Searching with OrgBeta key...")
        r = await client.post(f"{base_url}/mcp/sse", headers={"asila-api-key": beta_key}, json={"query": "PROJECT-NIGHTHAWK", "top_k": 5})
        print("OrgBeta search status:", r.status_code)
        print("OrgBeta search body:", r.text)
        
        # 4. Concurrent requests
        print("Firing concurrent requests...")
        async def call(key, q):
            return await client.post(f"{base_url}/mcp/sse", headers={'asila-api-key': key}, json={'query': q})
            
        r1, r2 = await asyncio.gather(call(alpha_key, 'test'), call(beta_key, 'test'))
        print("Concurrent Alpha status:", r1.status_code)
        print("Concurrent Beta status:", r2.status_code)
        
asyncio.run(main())
