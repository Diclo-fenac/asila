import requests
import time
import os
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "alpha-key-xxx"
TENANT_ID = "org_default"
AUTH_HEADERS = {}

def setup_auth():
    print("Setting up auth...")
    # Register
    reg_data = {
        "name": "Test User",
        "email": "test@alpha.com",
        "password": "Password123!",
        "tenant_id": TENANT_ID
    }
    headers = {"asila-api-key": API_KEY}
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
        return False
    
    token = resp.cookies.get("access_token")
    if token:
        AUTH_HEADERS["Authorization"] = f"Bearer {token}"
        AUTH_HEADERS["asila-api-key"] = API_KEY
        return True
    return False

def check_task_status(task_id):
    resp = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", headers=AUTH_HEADERS)
    if resp.status_code == 200:
        return resp.json().get("status")
    else:
        return f"Error: {resp.status_code}"

def upload_valid_file():
    doc_path = "test_worker_sim.md"
    with open(doc_path, "w") as f:
        f.write("# Worker Simulation\nThis is a temporary document to simulate worker failure.")
        
    url = f"{BASE_URL}/api/v1/documents/upload"
    with open(doc_path, 'rb') as f:
        files = {'file': (doc_path, f, 'text/markdown')}
        data = {'title': 'Worker Sim'}
        resp = requests.post(url, headers=AUTH_HEADERS, data=data, files=files)
        
    if os.path.exists(doc_path):
        os.remove(doc_path)
        
    if resp.status_code in [200, 202]:
        job_id = resp.json().get("job_id")
        print(f"Successfully uploaded file. Job ID: {job_id}")
        return job_id
    else:
        print("Failed to upload file:", resp.text)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_worker_simulation.py <action> [job_id]")
        print("Actions: upload, check")
        sys.exit(1)
        
    action = sys.argv[1]
    
    if not setup_auth():
        sys.exit(1)
        
    if action == "upload":
        job_id = upload_valid_file()
        if job_id:
            print(f"JOB_ID:{job_id}")
    elif action == "check":
        if len(sys.argv) < 3:
            print("Please specify job_id")
            sys.exit(1)
        job_id = sys.argv[2]
        status = check_task_status(job_id)
        print(f"STATUS:{status}")
