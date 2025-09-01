#!/usr/bin/env python3
"""
Minimal test - can we call a single simple tool?
"""

import asyncio
import logging
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Simple output model
class SimpleResult(BaseModel):
    status: str = Field(description="Status: completed or failed")
    message: str = Field(description="Summary message")


# Simple tool
@function_tool
async def simple_tool() -> str:
    """A simple test tool."""
    logger.info("*** SIMPLE TOOL WAS CALLED! ***")
    return "Tool executed successfully"


async def test_minimal():
    """Test the absolute minimal case"""

    logger.info("=" * 60)
    logger.info("MINIMAL TEST - One Tool + Structured Output")
    logger.info("=" * 60)

    model = LitellmModel(model="bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0")

    instructions = (
        "You have one tool called simple_tool. When asked to test, call it and report the result."
    )

    agent = Agent(
        name="Test Agent",
        instructions=instructions,
        model=model,
        tools=[simple_tool],
        output_type=SimpleResult,
    )

    task = "Please test the tool by calling simple_tool()."

    logger.info("Running agent...")
    try:
        result = await Runner.run(agent, input=task, max_turns=5)
        logger.info(f"Result: {result}")
        final = result.final_output_as(SimpleResult)
        logger.info(f"Status: {final.status}")
        logger.info(f"Message: {final.message}")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal())
