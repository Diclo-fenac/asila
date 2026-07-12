import asyncio
import httpx
import os

async def main():
    master_key = "sk-asila-master-key-12345"
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- GOAL 1: TENANT PROVISIONING ---")
        r1 = await client.post(f"{base_url}/api/v1/tenants/register", headers={"asila-api-key": master_key}, json={"name": "OrgAlphaCheck", "email": "alpha@test.com"})
        alpha_data = r1.json()
        print("OrgAlpha API Key returned!")
        alpha_key = alpha_data.get("api_key")
        
        r2 = await client.post(f"{base_url}/api/v1/tenants/register", headers={"asila-api-key": master_key}, json={"name": "OrgBetaCheck", "email": "beta@test.com"})
        beta_data = r2.json()
        print("OrgBeta API Key returned!")
        beta_key = beta_data.get("api_key")
        
        if not alpha_key or not beta_key:
            print("Failed to provision tenants.")
            return

        print("\n--- GOAL 1: UPLOADING CONFIDENTIAL DATA ---")
        files = {"file": ("secret.txt", b"PROJECT-NIGHTHAWK-CONFIDENTIAL", "text/plain")}
        r = await client.post(f"{base_url}/api/v1/documents/upload", headers={"asila-api-key": alpha_key}, files=files)
        print("Upload status:", r.status_code)
        
        print("Waiting 6 seconds for ingestion to complete...")
        await asyncio.sleep(6)
        
        print("\n--- GOAL 1: CROSS-TENANT SEARCH ---")
        r = await client.post(f"{base_url}/mcp/sse", headers={"asila-api-key": beta_key}, json={"query": "PROJECT-NIGHTHAWK", "top_k": 5})
        print("OrgBeta search status:", r.status_code)
        
        # 4. Concurrent requests
        print("\n--- GOAL 1: CONCURRENT REQUESTS ---")
        async def call(key, q):
            return await client.post(f"{base_url}/mcp/sse", headers={'asila-api-key': key}, json={'query': q})
            
        r1, r2 = await asyncio.gather(call(alpha_key, 'PROJECT-NIGHTHAWK'), call(beta_key, 'PROJECT-NIGHTHAWK'))
        print("Concurrent Alpha status:", r1.status_code)
        print("Concurrent Beta status:", r2.status_code)
        
        print("\n--- GOAL 5: PATH TRAVERSAL CHECK ---")
        files_pt = {"file": ("../../../../etc/passwd_test", b"fake file content", "text/plain")}
        r_pt = await client.post(f"{base_url}/api/v1/documents/upload", headers={"asila-api-key": alpha_key}, files=files_pt)
        print("Path Traversal Upload status:", r_pt.status_code)
        
asyncio.run(main())
