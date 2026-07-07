import asyncio
import re
import json
from mcp import ClientSession
from mcp.client.sse import sse_client
import sys

try:
    import tiktoken
except ImportError:
    print("tiktoken not found, please install it.")
    sys.exit(1)

API_KEY = "alpha-key-xxx" # From DB
URL = "http://127.0.0.1:8000/mcp/sse"

def extract_distance(result_text):
    try:
        data = json.loads(result_text)
        if isinstance(data, list):
            return [item.get("distance") for item in data if "distance" in item]
        return []
    except json.JSONDecodeError:
        distances = []
        lines = result_text.split("\n")
        for line in lines:
            match = re.search(r"Distance: ([\d\.]+)", line)
            if match:
                distances.append(float(match.group(1)))
        return distances

def extract_content_text(result_text):
    try:
        data = json.loads(result_text)
        if isinstance(data, list):
            return "\n---\n".join([item.get("content", "") for item in data])
        return result_text
    except json.JSONDecodeError:
        return result_text

def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

async def main():
    async with sse_client(URL, headers={"asila-api-key": API_KEY}) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to MCP.\n")
            
            # STEP 4.1 - Exact phrase search
            print("STEP 4.1 — Exact phrase search")
            q1 = "This is a sample paragraph for testing the multimodal ingestion engine. It contains some words and headers. We need at least 500 words so I am adding more text here to ensure we cross that threshold."
            print(f"Query: '{q1}'")
            res1 = await session.call_tool("search_verified_docs", {"query": q1, "top_k": 5})
            content1 = res1.content[0].text
            distances = extract_distance(content1)
            
            if not distances:
                print("Failed: No distances found.")
                print("Output was:\n", content1)
                sys.exit(1)
                
            top_similarity = 1.0 - distances[0]
            print(f"Top result similarity: {top_similarity:.4f}")
            if top_similarity > 0.85:
                print("-> PASS: Similarity is > 0.85\n")
            else:
                print("-> FAIL: Similarity is not > 0.85\n")
                
            # STEP 4.2 - Semantic / paraphrase search
            print("STEP 4.2 — Semantic / paraphrase search")
            q2 = "evaluating the system that imports various media types"
            print(f"Query: '{q2}'")
            res2 = await session.call_tool("search_verified_docs", {"query": q2, "top_k": 5})
            content2 = res2.content[0].text
            parsed_content2 = extract_content_text(content2)
            
            # We check if the expected chunk is in the results
            if "sample paragraph" in parsed_content2.lower() and len(extract_distance(content2)) > 0:
                 chunks = parsed_content2.split("---")
                 found_in_top_3 = False
                 for i, c in enumerate(chunks[:3]):
                     if "sample paragraph" in c.lower():
                         found_in_top_3 = True
                         break
                 if found_in_top_3:
                     print("-> PASS: Correct chunk appeared in top 3 results.\n")
                 else:
                     print("-> FAIL: Correct chunk not in top 3 results.\n")
            else:
                 print("-> FAIL: Correct chunk not found.\n")
                 
            # STEP 4.3 - Negative test
            print("STEP 4.3 — Negative test (hallucination guard)")
            q3 = "recipe for chocolate chip cookies"
            print(f"Query: '{q3}'")
            res3 = await session.call_tool("search_verified_docs", {"query": q3, "top_k": 5})
            content3 = res3.content[0].text
            print(f"Output: '{content3}'")
            if "No matching documents found" in content3 or content3.strip() == "[]" or "No relevant context found" in content3:
                print("-> PASS: System returned empty or graceful message without hallucination.\n")
            else:
                print("-> FAIL: System returned unexpected results.\n")
                
            # STEP 4.4 - Token budget enforcement
            print("STEP 4.4 — Token budget enforcement")
            q4 = "sample paragraph for testing"
            print(f"Query: '{q4}' with top_k=10")
            res4 = await session.call_tool("search_verified_docs", {"query": q4, "top_k": 10})
            content4 = res4.content[0].text
            tokens = count_tokens(content4)
            print(f"Total tokens returned: {tokens}")
            if tokens <= 2500:
                print("-> PASS: Tokens <= 2,500 limit.\n")
            else:
                print("-> FAIL: Tokens exceeded 2,500 limit.\n")

if __name__ == "__main__":
    asyncio.run(main())

