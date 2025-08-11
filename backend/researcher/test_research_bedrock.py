#!/usr/bin/env python3
"""
Test the full research pipeline with Bedrock OSS 120B model.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import the research function
from server import run_research_agent


async def test_research():
    """Test the research agent with Bedrock."""
    
    print("Testing Research Agent with Bedrock OSS 120B")
    print("=" * 50)
    print("Model: openai.gpt-oss-120b-1:0")
    print("Region: us-west-2")
    print("=" * 50)
    
    # Test with a specific topic
    topic = "Tesla earnings outlook for Q1 2025"
    
    print(f"\nResearch Topic: {topic}")
    print("-" * 50)
    
    try:
        result = await run_research_agent(topic)
        
        print("\nResearch Complete!")
        print("=" * 50)
        print(result)
        print("=" * 50)
        print("\n✅ Research with Bedrock completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_research())
    sys.exit(exit_code)