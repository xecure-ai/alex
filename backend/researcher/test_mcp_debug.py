#!/usr/bin/env python3
"""
Debug MCP server initialization
"""
import asyncio
from mcp_servers import create_playwright_mcp_server
from dotenv import load_dotenv

load_dotenv(override=True)


async def test_mcp_debug():
    """Test MCP server initialization and tool listing."""
    print("Testing MCP server initialization...")
    print("=" * 60)
    
    try:
        async with create_playwright_mcp_server() as mcp_server:
            print("✅ MCP server created successfully")
            
            # List available tools
            tools = await mcp_server.session.list_tools()
            print(f"\nAvailable tools: {len(tools.tools) if tools else 0}")
            
            if tools:
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
            else:
                print("  No tools available")
                
            # Try a simple navigation
            print("\nTrying to navigate to example.com...")
            result = await mcp_server.session.call_tool(
                "browser_navigate", 
                {"url": "https://example.com"}
            )
            print(f"Navigation result: {result}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_debug())