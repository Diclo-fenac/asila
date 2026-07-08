import requests

BASE_URL = "http://localhost:8000"
API_KEY = "alpha-key-xxx"
TENANT_ID = "org_default"

headers = {"asila-api-key": API_KEY}
login_data = {
    "email": "test@alpha.com",
    "password": "Password123!",
    "tenant_id": TENANT_ID
}
resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, headers=headers)
print("Login Status:", resp.status_code)
print("Login Body:", resp.text)
print("Cookies:", resp.cookies.get_dict())
