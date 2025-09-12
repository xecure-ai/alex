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
            max_turns=20  # Increased from 8 to potentially resolve Lambda execution issues
        )
        
        # COMPREHENSIVE DIAGNOSTIC LOGGING - Debug Step 1
        logger.info(f"===== CHARTER RUNNER RESULT DIAGNOSTICS =====")
        logger.info(f"Charter: Runner result type: {type(result)}")
        logger.info(f"Charter: Runner result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        
        # Log messages if available
        if hasattr(result, 'messages'):
            logger.info(f"Charter: Number of turns taken: {len(result.messages)}")
            for i, msg in enumerate(result.messages):
                msg_str = str(msg)[:500]  # First 500 chars
                logger.info(f"Charter: Turn {i}: {msg_str}")
                # Also log if the message contains tool calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"Charter: Turn {i} has {len(msg.tool_calls)} tool calls")
                    for j, tool_call in enumerate(msg.tool_calls):
                        logger.info(f"Charter: Turn {i} Tool {j}: {tool_call}")
        else:
            logger.info(f"Charter: Result has no 'messages' attribute")
        
        # Log final output details
        logger.info(f"Charter: Has final_output: {hasattr(result, 'final_output')}")
        if hasattr(result, 'final_output'):
            logger.info(f"Charter: Final output type: {type(result.final_output)}")
            logger.info(f"Charter: Final output length: {len(result.final_output) if result.final_output else 0}")
            logger.info(f"Charter: Final output preview: {result.final_output[:200] if result.final_output else 'None'}")
        
        # Log the conversation flow
        if hasattr(result, 'to_input_list'):
            input_list = result.to_input_list()
            logger.info(f"Charter: Conversation turns: {len(input_list)}")
            for i, msg in enumerate(input_list[:5]):  # First 5 messages
                logger.info(f"Charter: Message {i} - Role: {msg.get('role', 'unknown')}, Content length: {len(str(msg.get('content', '')))}")
                if msg.get('tool_calls'):
                    logger.info(f"Charter: Message {i} has {len(msg['tool_calls'])} tool calls")
        
        # Log raw responses to see what the model actually returned
        if hasattr(result, 'raw_responses'):
            logger.info(f"Charter: Number of raw responses: {len(result.raw_responses) if result.raw_responses else 0}")
            if result.raw_responses:
                for i, response in enumerate(result.raw_responses[:3]):  # First 3 responses
                    logger.info(f"Charter: Raw response {i} preview: {str(response)[:500]}")
        
        # Log context state after execution
        logger.info(f"Charter: Context charts after execution: {len(context.charts)} charts")
        logger.info(f"Charter: Chart keys: {list(context.charts.keys())}")
        
        return {
            'success': True,
            'message': 'Charts generated successfully',
            'final_output': result.final_output,
            'charts_generated': len(context.charts),
            'chart_keys': list(context.charts.keys())
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