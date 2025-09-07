"""
Report Writer Agent Lambda Handler
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any

from agents import Agent, Runner, trace

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from templates import REPORTER_INSTRUCTIONS
from agent import create_agent, format_portfolio_for_analysis

logger = logging.getLogger()
logger.setLevel(logging.INFO)

async def run_reporter_agent(job_id: str, portfolio_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the reporter agent to generate analysis."""
    
    # Create agent with tools
    model, tools = create_agent(job_id)
    
    # Format portfolio for analysis
    portfolio_summary = format_portfolio_for_analysis(portfolio_data, user_data)
    
    # Create task
    task = f"""Analyze this portfolio and generate a comprehensive report:

{portfolio_summary}

Remember to:
1. First get market insights for the key holdings
2. Generate a complete markdown analysis report
3. Store the report using update_report tool
"""
    
    # Run agent
    with trace("Portfolio Report Generation"):
        agent = Agent(
            name="Report Writer",
            instructions=REPORTER_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        result = await Runner.run(
            agent,
            input=task,
            max_turns=10
        )
        
        return {
            'success': True,
            'message': 'Report generated and stored',
            'final_output': result.final_output
        }

def lambda_handler(event, context):
    """
    Lambda handler expecting job_id in event.
    
    Expected event:
    {
        "job_id": "uuid",
        "portfolio_data": {...},  # Optional, will load from DB if not provided
        "user_data": {...}         # Optional user preferences
    }
    """
    try:
        logger.info(f"Reporter Lambda invoked with event: {json.dumps(event)[:500]}")
        
        # Parse event
        if isinstance(event, str):
            event = json.loads(event)
        
        job_id = event.get('job_id')
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'job_id is required'})
            }
        
        # Get portfolio data (provided or load from DB)
        portfolio_data = event.get('portfolio_data')
        if not portfolio_data:
            # Load from database
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from database.src.db_client import DatabaseClient
            
            db = DatabaseClient()
            job = asyncio.run(db.get_job(job_id))
            
            if not job:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': f'Job {job_id} not found'})
                }
            
            portfolio_data = job.request_payload.get('portfolio_data', {})
        
        user_data = event.get('user_data', {})
        
        # Run the agent
        result = asyncio.run(run_reporter_agent(job_id, portfolio_data, user_data))
        
        logger.info(f"Reporter completed for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in reporter: {e}", exc_info=True)
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
        "job_id": "test-job-123",
        "portfolio_data": {
            "accounts": [
                {
                    "name": "401(k)",
                    "cash_balance": 5000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "asset_class": "equity",
                                "current_price": 450
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 50,
                            "instrument": {
                                "name": "Vanguard Total Bond ETF",
                                "asset_class": "fixed_income",
                                "current_price": 80
                            }
                        }
                    ]
                }
            ]
        },
        "user_data": {
            "years_until_retirement": 25,
            "target_retirement_income": 75000
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))