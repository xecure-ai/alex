"""
Chart Maker Agent Lambda Handler
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any

from agents import Agent, Runner, trace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Import database package
from src import Database

from templates import CHARTER_INSTRUCTIONS
from agent import create_agent, CharterContext

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.info(f"Charter: Rate limit hit, retrying in {retry_state.next_action.sleep} seconds...")
)
async def run_charter_agent(job_id: str, portfolio_data: Dict[str, Any], db=None) -> Dict[str, Any]:
    """Run the charter agent to generate visualization data."""
    
    # Create agent with tools and context
    model, tools, task, context = create_agent(job_id, portfolio_data, db)
    
    # Run agent with context
    with trace("Charter Agent"):
        agent = Agent[CharterContext](  # Specify the context type
            name="Chart Maker",
            instructions=CHARTER_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        result = await Runner.run(
            agent,
            input=task,
            context=context,  # Pass the context
            max_turns=8
        )
        
        return {
            'success': True,
            'message': 'Charts generated successfully',
            'final_output': result.final_output
        }

def lambda_handler(event, context):
    """
    Lambda handler expecting job_id and portfolio_data in event.
    
    Expected event:
    {
        "job_id": "uuid",
        "portfolio_data": {...}
    }
    """
    try:
        logger.info(f"Charter Lambda invoked with event: {json.dumps(event)[:500]}")
        
        # Parse event
        if isinstance(event, str):
            event = json.loads(event)
        
        job_id = event.get('job_id')
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'job_id is required'})
            }
        
        portfolio_data = event.get('portfolio_data')
        if not portfolio_data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'portfolio_data is required'})
            }
        
        # Initialize database
        db = Database()
        
        # Run the agent
        result = asyncio.run(run_charter_agent(job_id, portfolio_data, db))
        
        logger.info(f"Charter completed for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in charter: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {
        "job_id": "550e8400-e29b-41d4-a716-446655440001",
        "portfolio_data": {
            "accounts": [
                {
                    "id": "acc1",
                    "name": "401(k)",
                    "type": "401k",
                    "cash_balance": 5000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "current_price": 450,
                                "allocation_asset_class": {"equity": 100},
                                "allocation_regions": {"north_america": 100},
                                "allocation_sectors": {"technology": 30, "healthcare": 15, "financials": 15, "consumer_discretionary": 20, "industrials": 20}
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 50,
                            "instrument": {
                                "name": "Vanguard Total Bond Market ETF",
                                "current_price": 80,
                                "allocation_asset_class": {"fixed_income": 100},
                                "allocation_regions": {"north_america": 100},
                                "allocation_sectors": {"treasury": 60, "corporate": 40}
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))