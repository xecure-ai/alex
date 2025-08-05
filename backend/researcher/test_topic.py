#!/usr/bin/env python3
"""
Test the researcher with a specific topic
"""
import asyncio
import sys
from context import get_agent_instructions
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document
from agents import Agent, Runner
from dotenv import load_dotenv

load_dotenv(override=True)


async def test_topic(topic):
    """Test the researcher agent with a specific topic."""
    print(f"Testing researcher agent with topic: {topic}")
    print("=" * 60)
    
    query = f"Research this investment topic: {topic}"
    
    try:
        async with create_playwright_mcp_server() as playwright_mcp:
            agent = Agent(
                name="Alex Investment Researcher",
                instructions=get_agent_instructions(),
                model="gpt-4.1-mini",
                tools=[ingest_financial_document],
                mcp_servers=[playwright_mcp],
            )
            
            result = await Runner.run(agent, input=query)
            
        print("\nRESULT:")
        print("=" * 60)
        print(result.final_output)
        print("=" * 60)
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Tesla stock price today"
    asyncio.run(test_topic(topic))