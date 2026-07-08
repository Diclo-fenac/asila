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
        else:
            sys.exit(1)
    except queue.Empty:
        sys.exit(1)

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
    requests.post(endpoint_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS)

    tool_call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_verified_docs",
            "arguments": {
                "query": "Aasila",
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
            print(f"✅ Received {len(content)} results for 'Aasila'")
            for c in content:
                print(f"   - {c.get('type')}: {str(c.get('text'))}")
        else:
            print("❌ Empty tool execution result")

if __name__ == "__main__":
    run_tests()
