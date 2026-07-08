import requests
import json
import sseclient
import threading
import queue
import time
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "alpha-key-xxx"
HEADERS = {"asila-api-key": API_KEY}
TENANT_ID = "org_default"

def test_pure_vector(query):
    print(f"\n--- Pure Vector Search (MCP `search_verified_docs`) ---")
    sse_response = requests.get(f"{BASE_URL}/mcp/sse", headers=HEADERS, stream=True)
    client = sseclient.SSEClient(sse_response)
    
    messages_queue = queue.Queue()
    
    def listen_sse():
        try:
            for event in client.events():
                if event.event == "endpoint":
                    messages_queue.put(("endpoint", event.data))
                elif event.event == "message":
                    messages_queue.put(("message", json.loads(event.data)))
        except Exception as e:
            pass

    t = threading.Thread(target=listen_sse, daemon=True)
    t.start()
    
    try:
        ev_type, ev_data = messages_queue.get(timeout=5)
        endpoint_url = BASE_URL + ev_data
    except queue.Empty:
        print("Timeout getting endpoint")
        return

    init_req = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
    }
    requests.post(endpoint_url, json=init_req, headers=HEADERS)
    messages_queue.get(timeout=5)
    requests.post(endpoint_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS)

    tool_call_req = {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "search_verified_docs", "arguments": {"query": query, "top_k": 3}}
    }
    requests.post(endpoint_url, json=tool_call_req, headers=HEADERS)
    ev_type, ev_data = messages_queue.get(timeout=15)
    
    if "error" in ev_data:
        print(f"Error: {ev_data['error']}")
    else:
        result = ev_data.get("result", {})
        content = result.get("content", [])
        if content:
            print("Received results:")
            for c in content:
                print(f"- {c.get('type')}: {str(c.get('text'))[:150]}...")
        else:
            print("No results.")

def test_graph_augmented(query):
    print(f"\n--- Graph-Augmented Search (Chat API) ---")
    reg_data = {"name": "Test User", "email": "test@alpha.com", "password": "Password123!", "tenant_id": TENANT_ID}
    requests.post(f"{BASE_URL}/api/v1/auth/register", json=reg_data, headers=HEADERS)
    
    login_data = {"email": "test@alpha.com", "password": "Password123!", "tenant_id": TENANT_ID}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, headers=HEADERS)
    token = resp.cookies.get("access_token")
    auth_headers = {"Authorization": f"Bearer {token}", "asila-api-key": API_KEY}
    
    chat_data = {"query": query}
    chat_resp = requests.post(f"{BASE_URL}/api/v1/chat/query", json=chat_data, headers=auth_headers)
    if chat_resp.status_code == 200:
        res = chat_resp.json()
        print("Answer:", res.get("answer"))
        print("\nCitations:")
        for c in res.get("citations", []):
            print(f"- [{c.get('document_title')}]: {c.get('chunk_text')[:100]}...")
    else:
        print("Error:", chat_resp.status_code, chat_resp.text)

if __name__ == "__main__":
    query = "What is the relationship between Aasila and MCP?"
    print(f"Testing Query: '{query}'")
    test_pure_vector(query)
    test_graph_augmented(query)
