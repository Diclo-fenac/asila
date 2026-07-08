import requests
import json
import os
import time

BASE_URL = "http://localhost:8000"
API_KEY = "alpha-key-xxx"
TENANT_ID = "org_default"

def setup_auth():
    # Register
    reg_data = {
        "name": "Test User",
        "email": "test@alpha.com",
        "password": "Password123!",
        "tenant_id": TENANT_ID
    }
    headers = {"asila-api-key": API_KEY}
    # ignore errors if already registered
    requests.post(f"{BASE_URL}/api/v1/auth/register", json=reg_data, headers=headers)
    
    # Login
    login_data = {
        "email": "test@alpha.com",
        "password": "Password123!",
        "tenant_id": TENANT_ID
    }
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, headers=headers)
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return None
    cookies = resp.cookies
    return cookies

def post_multipart(url, file_path, cookies):
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        data = {'title': os.path.basename(file_path)}
        headers = {"asila-api-key": API_KEY}
        resp = requests.post(url, headers=headers, cookies=cookies, data=data, files=files)
        try:
            return resp.json(), resp.status_code
        except:
            return resp.text, resp.status_code

def test_markdown(cookies):
    print("STEP 2.1 - Markdown ingestion")
    # Create md file
    with open("test_doc.md", "w") as f:
        for i in range(50):
            f.write(f"# Header {i}\nThis is a sample paragraph for testing the multimodal ingestion engine. It contains some words and headers. We need at least 500 words so I am adding more text here to ensure we cross that threshold.\n")
    
    resp_json, status = post_multipart(f"{BASE_URL}/api/v1/documents/upload", "test_doc.md", cookies)
    print(f"Status: {status}, Response: {resp_json}")
    if isinstance(resp_json, dict):
        return resp_json.get("task_id")
    return None

def test_poll(task_id):
    print(f"STEP 2.2 - Poll task status for {task_id}")
    # We poll using /api/v1/tasks/{task_id} which might require auth
    # Actually wait, is there a task poll endpoint? 
    pass

if __name__ == "__main__":
    cookies = setup_auth()
    if cookies:
        task_id = test_markdown(cookies)
        print("Task ID:", task_id)
