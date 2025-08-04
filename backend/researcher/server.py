"""
Alex Researcher Service - Investment Advice Agent
"""
import os
from typing import Dict, Any
from datetime import datetime, UTC

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from agents import Agent, Runner, function_tool
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

When providing investment advice:
1. Consider the user's specific question or topic
2. Provide specific, actionable recommendations
3. Break down complex topics into clear, understandable points
4. Use the ingest_financial_document tool to save your key insights

Important guidelines:
- Provide balanced advice considering both opportunities and risks
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
    
    # Create and run the agent
    agent = Agent(
        name="Alex Investment Researcher",
        instructions=AGENT_INSTRUCTIONS,
        model="gpt-4.1-mini",  # As specified in CLAUDE.md
        tools=[ingest_financial_document]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)