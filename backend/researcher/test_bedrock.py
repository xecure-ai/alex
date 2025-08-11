#!/usr/bin/env python3
"""
Test script for Bedrock integration with OSS 120B model.
Tests the model directly without the full research pipeline.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

# Suppress LiteLLM warnings about optional dependencies
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Load environment
load_dotenv(override=True)


async def test_bedrock_model():
    """Test the Bedrock OSS 120B model with a simple query."""
    
    print("Testing Bedrock OSS 120B model...")
    print(f"Region: us-west-2")
    print(f"Model: openai.gpt-oss-120b-1:0")
    print("-" * 50)
    
    try:
        # Set AWS region for Bedrock via environment variable
        # LiteLLM reads this for Bedrock connections
        os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
        
        # Configure Bedrock model
        # Back to converse route that worked
        model = LitellmModel(
            model="bedrock/converse/openai.gpt-oss-120b-1:0"
        )
        
        # Create a simple agent without MCP or tools for testing
        agent = Agent(
            name="Test Agent",
            instructions="You are a helpful assistant. Be concise.",
            model=model
        )
        
        # Test with a simple query
        query = "What are the key factors to consider when investing in technology stocks? Give me 3 bullet points."
        print(f"\nQuery: {query}\n")
        
        result = await Runner.run(agent, input=query, max_turns=1)
        
        print("Response from Bedrock OSS 120B:")
        print("-" * 50)
        print(result.final_output)
        print("-" * 50)
        print("\n✅ Bedrock integration working successfully!")
        
    except Exception as e:
        print(f"\n❌ Error testing Bedrock: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting tips:")
        print("1. Ensure you have AWS credentials configured (aws configure)")
        print("2. Verify you have access to the model in us-west-2")
        print("3. Check that your AWS credentials have Bedrock permissions")


if __name__ == "__main__":
    asyncio.run(test_bedrock_model())