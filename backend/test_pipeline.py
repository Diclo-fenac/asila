import requests
import json
import uuid

API_URL = "http://localhost:8000/api/v1"
TENANT_ID = "org_test_123"

def test_pipeline():
    # 1. Register User
    email = f"test_{uuid.uuid4()}@example.com"
    password = "Password123!"
    
    headers = {"X-Tenant-Id": TENANT_ID}
    
    print(f"Registering user: {email}")
    res = requests.post(f"{API_URL}/auth/register", headers=headers, json={
        "email": email,
        "password": password,
        "name": "Test User",
        "tenant_id": TENANT_ID
    })
    
    if res.status_code != 200:
        print(f"Registration failed: {res.status_code} {res.text}")
        return
        
    print("Registration successful!")
    
    # 2. Login
    print("Logging in...")
    res = requests.post(f"{API_URL}/auth/login", headers=headers, json={
        "email": email,
        "password": password,
        "tenant_id": TENANT_ID
    })
    
    if res.status_code != 200:
        print(f"Login failed: {res.status_code} {res.text}")
        return
        
    print("Login successful!")
    cookies = res.cookies
    print("Cookies:", cookies.get_dict())
    token = cookies.get("access_token")
    
    # 3. Chat Query Stream
    print("Sending chat query...")
    headers = {
        "X-Tenant-Id": TENANT_ID,
        "Cookie": f"access_token={token}"
    }
    
    res = requests.post(
        f"{API_URL}/chat/query/stream", 
        headers=headers,
        cookies=cookies,
        json={"query": "When is the water supply scheduled for ward 12?"},
        stream=True
    )
    
    print("Sent Headers:", res.request.headers)
    
    if res.status_code != 200:
        print(f"Chat query failed: {res.status_code} {res.text}")
        return
        
    print("Chat query successful! Stream output:")
    for line in res.iter_lines():
        if line:
            print(line.decode('utf-8'))

if __name__ == "__main__":
    test_pipeline()
