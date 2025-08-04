"""
Test script for the Alex Researcher service
"""
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

async def test_researcher():
    """Test the researcher service locally."""
    
    base_url = "http://localhost:8000"
    
    print("Testing Alex Researcher Service")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # 1. Test health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            health_data = response.json()
            print(f"   ✓ Service status: {health_data['status']}")
            print(f"   ✓ Alex API configured: {health_data['alex_api_configured']}")
        except Exception as e:
            print(f"   ✗ Health check failed: {e}")
            return
        
        # 2. Test research endpoint
        print("\n2. Testing research endpoint...")
        print("   Asking for tech stock recommendations...")
        
        research_request = {
            "topic": "Top technology stocks to invest in for AI and cloud computing growth with strong fundamentals in 2025"
        }
        
        try:
            response = await client.post(
                f"{base_url}/research",
                json=research_request,
                timeout=60.0  # Longer timeout for AI processing
            )
            response.raise_for_status()
            
            result = response.text  # Now returns plain text
            print(f"\n   ✓ Research completed!")
            print(f"\n   Investment Advice:")
            print("   " + "-" * 40)
            # Print advice with proper formatting
            for line in result.split('\n'):
                if line.strip():
                    print(f"   {line}")
            
        except httpx.TimeoutException:
            print("   ✗ Request timed out (this might mean the agent is working but taking time)")
        except Exception as e:
            print(f"   ✗ Research failed: {e}")
    
    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    print("\nMake sure the server is running with:")
    print("  uv run server.py")
    print("\nOr in another terminal:")
    print("  uv run uvicorn server:app --reload")
    print("\nPress Ctrl+C to cancel if server is not running...")
    print()
    
    asyncio.run(test_researcher())