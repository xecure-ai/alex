"""
Alex Researcher Service - Investment Advice Agent
"""
import os
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner

# Import from our modules
from context import get_agent_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document

# Load environment
load_dotenv(override=True)

app = FastAPI(title="Alex Researcher Service")

# Request model  
class ResearchRequest(BaseModel):
    topic: Optional[str] = None  # Optional - if not provided, agent picks a topic


async def run_research_agent(topic: str = None) -> str:
    """Run the research agent to generate investment advice."""
    
    # Prepare the user query
    if topic:
        query = f"Research this investment topic: {topic}"
    else:
        query = DEFAULT_RESEARCH_PROMPT
    
    # Create and run the agent with MCP server
    async with create_playwright_mcp_server() as playwright_mcp:
        agent = Agent(
            name="Alex Investment Researcher",
            instructions=get_agent_instructions(),
            model="gpt-4.1-mini",
            tools=[ingest_financial_document],
            mcp_servers=[playwright_mcp]
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
    
    The agent will:
    1. Browse current financial websites for data
    2. Analyze the information found
    3. Store the analysis in the knowledge base
    
    If no topic is provided, the agent will pick a trending topic.
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
        "alex_api_configured": bool(os.getenv("ALEX_API_ENDPOINT") and os.getenv("ALEX_API_KEY")),
        "timestamp": datetime.now(UTC).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)