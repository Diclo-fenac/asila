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
    
    ev_type, ev_data = messages_queue.get(timeout=5)
    endpoint_url = BASE_URL + ev_data

    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    requests.post(endpoint_url, json=init_req, headers=HEADERS)
    messages_queue.get(timeout=5)
    requests.post(endpoint_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS)

    tools_list_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    requests.post(endpoint_url, json=tools_list_req, headers=HEADERS)
    ev_type, ev_data = messages_queue.get(timeout=5)
    
    tools = ev_data.get("result", {}).get("tools", [])
    print(json.dumps(tools, indent=2))

if __name__ == "__main__":
    run_tests()
