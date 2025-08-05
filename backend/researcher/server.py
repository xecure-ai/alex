"""
Alex Researcher Service - Investment Advice Agent
"""
import os
import json
from typing import Dict, Any
from datetime import datetime, UTC

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from agents import Agent, Runner, function_tool
from agents.mcp import MCPServerStdio
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment
load_dotenv(override=True)

app = FastAPI(title="Alex Researcher Service")

# Configuration
ALEX_API_ENDPOINT = os.getenv("ALEX_API_ENDPOINT")
ALEX_API_KEY = os.getenv("ALEX_API_KEY")

# Request model
class ResearchRequest(BaseModel):
    topic: str

def _ingest(document: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to make the actual API call."""
    with httpx.Client() as client:
        response = client.post(
            f"{ALEX_API_ENDPOINT}/ingest",
            json=document,
            headers={"x-api-key": ALEX_API_KEY},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def ingest_with_retries(document: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest with retry logic for SageMaker cold starts."""
    return _ingest(document)

# Tool for ingesting documents to Alex knowledge base
@function_tool
def ingest_financial_document(topic: str, analysis: str) -> Dict[str, Any]:
    """
    Ingest a financial document into the Alex knowledge base.
    
    Args:
        topic: The topic or subject of the analysis (e.g., "AAPL", "Retirement Planning", "Tech Sector Outlook")
        analysis: Detailed analysis or advice
    
    Returns:
        Dictionary with success status and document ID
    """
    if not ALEX_API_ENDPOINT or not ALEX_API_KEY:
        return {
            "success": False,
            "error": "Alex API not configured. Running in local mode."
        }
    
    document = {
        "text": analysis,
        "metadata": {
            "topic": topic,
            "timestamp": datetime.now(UTC).isoformat()
        }
    }
    
    try:
        result = ingest_with_retries(document)
        return {
            "success": True,
            "document_id": result.get("documentId"),
            "message": f"Successfully ingested analysis for {topic}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Agent configuration
AGENT_INSTRUCTIONS = """You are an expert financial advisor and investment researcher for the Alex platform.
Your role is to provide thoughtful, well-researched investment advice and analysis.

You have access to web browsing capabilities through MCP tools. The key tools you should use are:
- browser_navigate - Navigate to a specific URL (e.g., financial websites)
- browser_snapshot - Take a snapshot of the current page to read its content
- browser_click - Click on elements if needed
- browser_type - Type text into fields if needed
- browser_wait_for - Wait for content to load

IMPORTANT: Use browser_navigate to visit financial websites like Yahoo Finance, Google Finance, or MarketWatch to get current stock prices and news.

When providing investment advice:
1. Use web browsing to gather current, accurate information
2. Consider the user's specific question or topic
3. Provide specific, actionable recommendations based on your research
4. Break down complex topics into clear, understandable points
5. Cite specific sources and data points from your web research
6. Use the ingest_financial_document tool to save your key insights

Important guidelines:
- ALWAYS start by using browser_navigate to visit a financial website
- After navigating, use browser_snapshot to read the page content
- Provide balanced advice considering both opportunities and risks
- Include specific numbers, dates, and sources from your research
- Adapt your response to the topic (stocks, retirement, asset allocation, etc.)
- Create analyses that will be valuable for long-term reference
- Focus on fundamentals and long-term value
- Save your analysis using the tool with a clear topic name
- After using the tool, briefly confirm the advice was saved
"""

async def run_research_agent(topic: str) -> str:
    """Run the research agent to generate investment advice."""
    
    # Prepare the user query
    query = f"Research topic: {topic}"
    
    # Configure Playwright MCP server
    playwright_params = {
        "command": "npx",
        "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox", "--ignore-https-errors", "--executable-path", "/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"]
    }
    
    # Create and run the agent with MCP server
    async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as mcp_server:
        agent = Agent(
            name="Alex Investment Researcher",
            instructions=AGENT_INSTRUCTIONS,
            model="gpt-4.1-mini",  # As specified in CLAUDE.md
            tools=[ingest_financial_document],
            mcp_servers=[mcp_server]
        )
        
        result = await Runner.run(
            agent,
            input=query
        )
    
    return result.final_output

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Alex Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.post("/research")
async def research(request: ResearchRequest) -> str:
    """
    Generate investment research and advice.
    
    The agent will analyze the topic, provide advice, and automatically
    ingest relevant documents into the Alex knowledge base.
    """
    try:
        response = await run_research_agent(request.topic)
        return response
    except Exception as e:
        print(f"Error in research endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "service": "Alex Researcher",
        "status": "healthy",
        "alex_api_configured": bool(ALEX_API_ENDPOINT and ALEX_API_KEY),
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.get("/mcp-browser-test")
async def mcp_browser_test():
    """Test MCP browser functionality by navigating to a page with dynamic content."""
    try:
        playwright_params = {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox", "--ignore-https-errors", "--executable-path", "/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"]
        }
        
        async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as server:
            # Navigate to httpbin.org to get current headers/IP (dynamic content)
            navigate_result = await server.session.call_tool(
                "browser_navigate", 
                {"url": "https://httpbin.org/headers"}
            )
            
            # Take a snapshot
            snapshot_result = await server.session.call_tool(
                "browser_snapshot", 
                {}
            )
            
            return {
                "status": "success",
                "browser_working": True,
                "navigate_result": navigate_result.model_dump() if navigate_result else None,
                "snapshot_preview": str(snapshot_result.content[0].text)[:1000] if snapshot_result and snapshot_result.content else None
            }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "browser_working": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/mcp-stock-test")
async def mcp_stock_test():
    """Test MCP browser by fetching actual stock data."""
    try:
        playwright_params = {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox", "--ignore-https-errors", "--executable-path", "/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"]
        }
        
        async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as server:
            # Navigate to Yahoo Finance for AAPL
            navigate_result = await server.session.call_tool(
                "browser_navigate", 
                {"url": "https://finance.yahoo.com/quote/AAPL"}
            )
            
            # Wait a bit for page to load
            await server.session.call_tool(
                "browser_wait_for",
                {"time": 2000}
            )
            
            # Take a snapshot
            snapshot_result = await server.session.call_tool(
                "browser_snapshot", 
                {}
            )
            
            snapshot_text = str(snapshot_result.content[0].text) if snapshot_result and snapshot_result.content else "No snapshot"
            
            # Look for price in the snapshot
            import re
            price_match = re.search(r'\$?(\d+\.\d+)', snapshot_text)
            
            return {
                "status": "success",
                "browser_working": True,
                "found_price": price_match.group(0) if price_match else "No price found",
                "snapshot_preview": snapshot_text[:2000]
            }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "browser_working": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/mcp-test")
async def mcp_test():
    """Test MCP server connection and list available tools."""
    try:
        # Configure Playwright MCP server
        playwright_params = {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox", "--ignore-https-errors", "--executable-path", "/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"]
        }
        
        # Test MCP server connection
        async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as server:
            # Get available tools
            tools = await server.session.list_tools()
            
            return {
                "status": "success",
                "mcp_connected": True,
                "tools_count": len(tools.tools) if tools else 0,
                "tools": [{"name": tool.name, "description": tool.description} for tool in tools.tools] if tools else []
            }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "mcp_connected": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/test-agent-browser")
async def test_agent_browser():
    """Direct test of agent with browser tools."""
    playwright_params = {
        "command": "npx",
        "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox", "--executable-path", "/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome"]
    }
    
    async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as mcp_server:
        agent = Agent(
            name="Test Agent",
            instructions="Use browser_navigate to go to https://example.com, then use browser_snapshot to tell me what you see.",
            model="gpt-4.1-mini",
            mcp_servers=[mcp_server]
        )
        
        result = await Runner.run(
            agent,
            input="Please navigate to example.com and tell me what's on the page"
        )
    
    return {"result": result.final_output}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)