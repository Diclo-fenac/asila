import requests
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
    
    # Extract token
    token = resp.cookies.get("access_token")
    if token:
        AUTH_HEADERS["Authorization"] = f"Bearer {token}"
        AUTH_HEADERS["asila-api-key"] = API_KEY
        return True
    return False

def test_unsupported_file():
    print("Creating dummy unsupported files...")
    exe_file = "test_unsupported.exe"
    with open(exe_file, "w") as f:
        f.write("DUMMY EXE CODE")
        
    zip_file = "test_unsupported.zip"
    with open(zip_file, "w") as f:
        f.write("DUMMY ZIP CODE")

    url = f"{BASE_URL}/api/v1/documents/upload"
    
    # Test EXE
    print("Testing upload of .exe file...")
    with open(exe_file, 'rb') as f:
        files = {'file': (exe_file, f, 'application/x-msdownload')}
        data = {'title': exe_file}
        resp = requests.post(url, headers=AUTH_HEADERS, data=data, files=files)
        
    print(f"HTTP Status: {resp.status_code}")
    print(f"HTTP Response: {resp.text}")
    try:
        res_json = resp.json()
        detail = res_json.get("detail", "")
        expected = "File type .exe is not supported. Supported types: .md, .pdf, .png, .py, .js, .go, .html"
        if detail == expected:
            print("✅ PASS: Correct rejection message returned for .exe")
        else:
            print(f"❌ FAIL: Expected '{expected}', got '{detail}'")
    except Exception as e:
        print(f"❌ FAIL: Could not parse response JSON: {e}")

    # Clean up
    if os.path.exists(exe_file):
        os.remove(exe_file)
    if os.path.exists(zip_file):
        os.remove(zip_file)

if __name__ == "__main__":
    if setup_auth():
        test_unsupported_file()
    else:
        sys.exit(1)
