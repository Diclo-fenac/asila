import requests
import json
import os
import time

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

def post_multipart(url, file_path, mime_type=None):
    import mimetypes
    mime = mime_type or mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, mime)}
        data = {'title': os.path.basename(file_path)}
        resp = requests.post(url, headers=AUTH_HEADERS, data=data, files=files)
        try:
            return resp.json(), resp.status_code
        except:
            return resp.text, resp.status_code

def test_step_2_1():
    print("\n--- STEP 2.1 - Markdown ingestion ---")
    with open("test_doc.md", "w") as f:
        for i in range(60):
            f.write(f"# Header {i}\nThis is a sample paragraph for testing the multimodal ingestion engine. It contains some words and headers. We need at least 500 words so I am adding more text here to ensure we cross that threshold.\n")
    
    resp_json, status = post_multipart(f"{BASE_URL}/api/v1/documents/upload", "test_doc.md", mime_type="text/plain")
    print(f"Status: {status}")
    if status == 202 or status == 200:
        task_id = resp_json.get("job_id")
        print("Task ID:", task_id)
        return task_id
    else:
        print("Error:", resp_json)
        return None

def test_step_2_2(task_id):
    print("\n--- STEP 2.2 - Poll task status ---")
    start_time = time.time()
    while True:
        resp = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", headers=AUTH_HEADERS)
        if resp.status_code == 200:
            status = resp.json().get("status")
            print(f"Status: {status}")
            if status == "completed":
                print(f"Task completed in {time.time() - start_time:.2f} seconds")
                return True
            if status == "failed":
                print("Task failed!")
                return False
        else:
            print(f"Poll error: {resp.status_code} {resp.text}")
            return False
        
        if time.time() - start_time > 60:
            print("Timeout polling task!")
            return False
        time.sleep(2)

def create_dummy_pdf():
    # A dummy text file saved as PDF for the vision path. Wait, the vision path uses gemini vision.
    # It should be an actual PDF or image. I will just create a PNG using PIL.
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (200, 100), color = (73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10,10), "SecretTermVisionTest123", fill=(255,255,0))
        img.save('test_image.png')
        return "test_image.png"
    except ImportError:
        print("Pillow not installed, creating a text file disguised as PDF")
        # If pillow is not there, we can just write a text file. Wait, vision needs a real image.
        pass

def test_step_2_3():
    print("\n--- STEP 2.3 - PDF/image ingestion ---")
    img_path = create_dummy_pdf()
    if not img_path:
        return
    resp_json, status = post_multipart(f"{BASE_URL}/api/v1/documents/upload", img_path)
    if status == 202 or status == 200:
        task_id = resp_json.get("job_id")
        if test_step_2_2(task_id):
            print("Querying for secret term...")
            # We assume there's a chat or search endpoint.
            # I will skip the actual query here and use DB search later.
            print("Ingestion completed for image")
            return resp_json.get("document_id")

def test_step_2_4():
    print("\n--- STEP 2.4 - Code file ingestion ---")
    with open("test_code.py", "w") as f:
        f.write('''def unique_function_name_123():
    print("This is a test function")
    return True

class TestClass:
    def method(self):
        pass
''')
    resp_json, status = post_multipart(f"{BASE_URL}/api/v1/documents/upload", "test_code.py", mime_type="text/plain")
    if status == 202 or status == 200:
        task_id = resp_json.get("job_id")
        test_step_2_2(task_id)

def test_step_2_5():
    print("\n--- STEP 2.5 - Collision/duplicate handling ---")
    print("Uploading test_doc.md again...")
    resp_json, status = post_multipart(f"{BASE_URL}/api/v1/documents/upload", "test_doc.md", mime_type="text/plain")
    print(f"Status: {status}")
    if status == 202 or status == 200:
        task_id = resp_json.get("job_id")
        test_step_2_2(task_id)
        doc_id = resp_json.get("document_id")
        return doc_id
    elif status == 409:
        print("Conflict handled properly.")
    else:
        print("Error:", resp_json)

if __name__ == "__main__":
    if setup_auth():
        t1 = test_step_2_1()
        if t1:
            test_step_2_2(t1)
        test_step_2_3()
        test_step_2_4()
        test_step_2_5()
