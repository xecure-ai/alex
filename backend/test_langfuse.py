import os
import asyncio
from dotenv import load_dotenv
import logfire
from langfuse import get_client
from agents import Agent, Runner, trace, function_tool

load_dotenv(override=True)

@function_tool
async def get_meaning() -> str:
    """Get the meaning of life from the universe"""
    return "42"

async def test_langfuse_integration():
    # Only proceed if LangFuse env vars are set
    if not os.getenv("LANGFUSE_SECRET_KEY"):
        print("❌ LangFuse not configured - skipping observability")
        return

    print("🔧 Configuring Logfire...")
    logfire.configure(
        service_name='alex_test',
        send_to_logfire=False
    )

    print("📡 Instrumenting OpenAI Agents SDK...")
    logfire.instrument_openai_agents()

    print("✅ Connecting to LangFuse...")
    langfuse = get_client()
    langfuse.auth_check()

    print("🤖 Creating test agent...")
    with trace("Test Meaning of Life"):
        agent = Agent(
            name="Philosopher",
            instructions="You are a wise philosopher. Use the get_meaning tool to find the meaning of life.",
            model="gpt-4o-mini",
            tools=[get_meaning]
        )

        result = await Runner.run(
            agent,
            "What is the meaning of life?",
            max_turns=3
        )

        print(f"📝 Result: {result.final_output}")

    print("✨ Check LangFuse dashboard for traces!")
    print(f"🔗 {os.getenv('LANGFUSE_HOST')}")

if __name__ == "__main__":
    asyncio.run(test_langfuse_integration())