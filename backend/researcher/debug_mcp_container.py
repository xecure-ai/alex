#!/usr/bin/env python3
"""
Debug MCP server in container
"""
import os
import asyncio
import subprocess
from mcp_servers import create_playwright_mcp_server

print(f"Running as UID: {os.getuid()}")
print(f"Chromium exists: {os.path.exists('/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome')}")

# Test npx command
print("\nTesting npx command...")
result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
print(f"npx version: {result.stdout.strip()}")

# Test MCP server startup
print("\nTesting MCP server startup...")
async def test():
    try:
        mcp = create_playwright_mcp_server(timeout_seconds=10)
        print(f"MCP server created with params: {mcp.params}")
        
        async with mcp as server:
            print("MCP server started successfully")
            tools = await server.session.list_tools()
            print(f"Available tools: {len(tools.tools) if tools else 0}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())