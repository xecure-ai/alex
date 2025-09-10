"""
Retirement Specialist Agent Lambda Handler
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

from templates import RETIREMENT_INSTRUCTIONS
from agent import create_agent, RetirementContext

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_user_preferences(job_id: str) -> Dict[str, Any]:
    """Load user preferences from database."""
    try:
        db = Database()
        
        # Get the job to find the user
        job = db.jobs.find_by_id(job_id)
        if job and job.get('clerk_user_id'):
            # Get user preferences
            user = db.users.find_by_clerk_id(job['clerk_user_id'])
            if user:
                return {
                    'years_until_retirement': user.get('years_until_retirement', 30),
                    'target_retirement_income': float(user.get('target_retirement_income', 80000)),
                    'current_age': 40  # Default for now
                }
    except Exception as e:
        logger.warning(f"Could not load user data: {e}. Using defaults.")
    
    return {
        'years_until_retirement': 30,
        'target_retirement_income': 80000.0,
        'current_age': 40
    }

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.info(f"Retirement: Rate limit hit, retrying in {retry_state.next_action.sleep} seconds...")
)
async def run_retirement_agent(job_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the retirement specialist agent."""
    
    # Get user preferences
    user_preferences = get_user_preferences(job_id)
    
    # Initialize database
    db = Database()
    
    # Create agent with tools and context
    model, tools, task, context = create_agent(job_id, portfolio_data, user_preferences, db)
    
    # Run agent with context
    with trace("Retirement Agent"):
        agent = Agent[RetirementContext](  # Specify the context type
            name="Retirement Specialist",
            instructions=RETIREMENT_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        result = await Runner.run(
            agent,
            input=task,
            context=context,  # Pass the context
            max_turns=5
        )
        
        return {
            'success': True,
            'message': 'Retirement analysis completed',
            'final_output': result.final_output
        }

def lambda_handler(event, context):
    """
    Lambda handler expecting job_id in event.
    
    Expected event:
    {
        "job_id": "uuid",
        "portfolio_data": {...}  # Optional, will load from DB if not provided
    }
    """
    try:
        logger.info(f"Retirement Lambda invoked with event: {json.dumps(event)[:500]}")
        
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
            # Try to load from database
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from src import Database
                
                db = Database()
                job = db.jobs.find_by_id(job_id)
                if job:
                    portfolio_data = job.get('request_payload', {}).get('portfolio_data', {})
                else:
                    return {
                        'statusCode': 404,
                        'body': json.dumps({'error': f'Job {job_id} not found'})
                    }
            except Exception as e:
                logger.error(f"Could not load portfolio from database: {e}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No portfolio data provided'})
                }
        
        # Run the agent
        result = asyncio.run(run_retirement_agent(job_id, portfolio_data))
        
        logger.info(f"Retirement completed for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in retirement: {e}", exc_info=True)
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
        "job_id": "test-retirement-123",
        "portfolio_data": {
            "accounts": [
                {
                    "name": "401(k)",
                    "type": "retirement",
                    "cash_balance": 10000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "current_price": 450,
                                "allocation_asset_class": {"equity": 100}
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 100,
                            "instrument": {
                                "name": "Vanguard Total Bond Market ETF",
                                "current_price": 75,
                                "allocation_asset_class": {"fixed_income": 100}
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))