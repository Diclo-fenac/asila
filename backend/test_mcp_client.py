import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://127.0.0.1:8000/mcp/sse", headers={"asila-api-key": "sk-asila-q06dsttwgPfxy-4QHmI_aw4PC1NoZtD6IjN9on8HkcI"}) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("INITIALIZED!")
            
            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            
            result = await session.call_tool("search_verified_docs", {"query": "MCP"})
            print("SEARCH RESULT:")
            for item in result.content:
                print(item.text)

if __name__ == "__main__":
    asyncio.run(main())
