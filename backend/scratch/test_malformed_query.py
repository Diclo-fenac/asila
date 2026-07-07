import requests
import json
import sseclient
import threading
import queue
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "alpha-key-xxx"
HEADERS = {"asila-api-key": API_KEY}

def run_tests():
    print("Connecting to SSE endpoint...")
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
            print(f"Received endpoint: {endpoint_url}")
        else:
            print(f"Failed to get endpoint event: {ev_type}, {ev_data}")
            sys.exit(1)
    except queue.Empty:
        print("Timeout waiting for endpoint event")
        sys.exit(1)

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
    messages_queue.get(timeout=5)
    
    # Send initialized notification
    requests.post(endpoint_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS)

    # Tool execution with missing 'query' argument
    tool_call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_verified_docs",
            "arguments": {
                "top_k": 3
            }
        }
    }
    
    print("Calling search_verified_docs with missing 'query'...")
    resp = requests.post(endpoint_url, json=tool_call_req, headers=HEADERS)
    print(f"HTTP Status: {resp.status_code}")
    print(f"HTTP Response text: {resp.text}")
    
    try:
        ev_type, ev_data = messages_queue.get(timeout=10)
        print("SSE message received:")
        print(json.dumps(ev_data, indent=2))
    except queue.Empty:
        print("Timeout waiting for SSE tool call response")

if __name__ == "__main__":
    run_tests()
