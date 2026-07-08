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

def run_tests():
    print("STEP 3.1: Connect to SSE endpoint")
    sse_response = requests.get(f"{BASE_URL}/mcp/sse", headers=HEADERS, stream=True)
    sse_response.raise_for_status()
    
    client = sseclient.SSEClient(sse_response)
    
    endpoint_url = None
    messages_queue = queue.Queue()
    
    def listen_sse():
        try:
            for event in client.events():
                if event.event == "endpoint":
                    messages_queue.put(("endpoint", event.data))
                elif event.event == "message":
                    messages_queue.put(("message", json.loads(event.data)))
        except Exception as e:
            messages_queue.put(("error", str(e)))

    t = threading.Thread(target=listen_sse, daemon=True)
    t.start()
    
    try:
        ev_type, ev_data = messages_queue.get(timeout=5)
        if ev_type == "endpoint":
            endpoint_url = BASE_URL + ev_data
            print(f"✅ Received endpoint: {endpoint_url}")
        else:
            print(f"❌ Failed to get endpoint event: {ev_type}, {ev_data}")
            sys.exit(1)
    except queue.Empty:
        print("❌ Timeout waiting for endpoint event")
        sys.exit(1)

    print("\nSTEP 3.2: Tool listing")
    # Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }
    requests.post(endpoint_url, json=init_req, headers=HEADERS)
    
    ev_type, ev_data = messages_queue.get(timeout=5)
    print("Init response:", json.dumps(ev_data, indent=2))
    
    # Send initialized notification
    requests.post(endpoint_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS)

    # tools/list
    tools_list_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    requests.post(endpoint_url, json=tools_list_req, headers=HEADERS)
    ev_type, ev_data = messages_queue.get(timeout=5)
    
    tools = ev_data.get("result", {}).get("tools", [])
    tool_names = [t["name"] for t in tools]
    print(f"Tools available: {tool_names}")
    if "search_verified_docs" in tool_names:
        print("✅ search_verified_docs is listed")
    else:
        print("❌ search_verified_docs missing")

    print("\nSTEP 3.3: Tool execution via MCP")
    tool_call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_verified_docs",
            "arguments": {
                "query": "Welcome",
                "top_k": 3
            }
        }
    }
    requests.post(endpoint_url, json=tool_call_req, headers=HEADERS)
    ev_type, ev_data = messages_queue.get(timeout=15)
    
    if "error" in ev_data:
        print(f"❌ Tool call error: {ev_data['error']}")
    else:
        result = ev_data.get("result", {})
        content = result.get("content", [])
        if content:
            print(f"✅ Received {len(content)} results from tool call")
            for c in content:
                print(f"   - {c.get('type')}: {str(c.get('text'))[:100]}...")
        else:
            print("❌ Empty tool execution result")

    print("\nSTEP 3.4: Auth rejection test")
    bad_headers = {"asila-api-key": "bad-key"}
    print("Sending request with bad key...")
    resp = requests.post(endpoint_url, json=tool_call_req, headers=bad_headers)
    print(f"Response status: {resp.status_code}")
    print(f"Response text: {resp.text}")
    
    if resp.status_code != 200 and "Authentication failed" in resp.text:
        print("✅ Auth rejection returned rich error string")
    else:
        print("❌ Auth rejection test failed or didn't match expected output")

if __name__ == "__main__":
    run_tests()
