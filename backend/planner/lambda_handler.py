"""
Financial Planner Orchestrator Lambda Handler
Receives SQS messages and coordinates portfolio analysis across specialized agents.
"""

import os
import json
import asyncio
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging

from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

# Try to load .env file if available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Import database package
from src.models import Database
from src.schemas import JobUpdate

from templates import ORCHESTRATOR_INSTRUCTIONS, ANALYSIS_REQUEST_TEMPLATE

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
db = Database()
lambda_client = boto3.client('lambda')

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-7-sonnet-20250219-v1:0')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-west-2')

# Add the 'us.' prefix for the inference profile if not already present
if BEDROCK_MODEL_ID.startswith('anthropic.') and not BEDROCK_MODEL_ID.startswith('us.'):
    BEDROCK_MODEL_ID = f'us.{BEDROCK_MODEL_ID}'

# Lambda function names from environment
TAGGER_FUNCTION = os.getenv('TAGGER_FUNCTION', 'alex-tagger')
REPORTER_FUNCTION = os.getenv('REPORTER_FUNCTION', 'alex-reporter')
CHARTER_FUNCTION = os.getenv('CHARTER_FUNCTION', 'alex-charter')
RETIREMENT_FUNCTION = os.getenv('RETIREMENT_FUNCTION', 'alex-retirement')

# Check if we're in local testing mode
MOCK_LAMBDAS = os.getenv('MOCK_LAMBDAS', 'false').lower() == 'true'

# Store current job_id for tools to access
current_job_id = None
current_portfolio_data = None


async def invoke_lambda_agent(agent_name: str, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic Lambda agent invocation.
    
    Args:
        agent_name: Display name of the agent
        function_name: Lambda function name
        payload: Payload to send
        
    Returns:
        Agent response
    """
    try:
        logger.info(f"Invoking {agent_name}: {function_name}")
        
        if MOCK_LAMBDAS:
            # Local testing mode - import and run agents directly
            logger.info(f"MOCK_LAMBDAS enabled - running {agent_name} locally")
            
            if agent_name == "Reporter":
                from backend.reporter.lambda_handler import lambda_handler as reporter_handler
                result = reporter_handler({'body': json.dumps(payload)}, None)
            elif agent_name == "Charter":
                from backend.charter.lambda_handler import lambda_handler as charter_handler
                result = charter_handler({'body': json.dumps(payload)}, None)
            elif agent_name == "Retirement":
                from backend.retirement.lambda_handler import lambda_handler as retirement_handler
                result = retirement_handler({'body': json.dumps(payload)}, None)
            else:
                raise ValueError(f"Unknown agent: {agent_name}")
        else:
            # Production mode - invoke Lambda
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
        
        # Unwrap Lambda response if it has the standard format
        if isinstance(result, dict) and 'statusCode' in result and 'body' in result:
            if isinstance(result['body'], str):
                try:
                    result = json.loads(result['body'])
                except json.JSONDecodeError:
                    result = {'message': result['body']}
            else:
                result = result['body']
        
        logger.info(f"{agent_name} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error invoking {agent_name}: {e}")
        return {'error': str(e)}


@function_tool
async def invoke_reporter() -> str:
    """
    Invoke the Report Writer Lambda to generate portfolio analysis narrative.
    The Reporter agent will analyze the portfolio and save results to the database.
    
    Returns:
        Confirmation message
    """
    global current_job_id
    
    result = await invoke_lambda_agent(
        "Reporter",
        REPORTER_FUNCTION,
        {'job_id': current_job_id}
    )
    
    if 'error' in result:
        return f"Reporter agent failed: {result['error']}"
    
    return "Reporter agent completed successfully. Portfolio analysis narrative has been generated and saved."


@function_tool
async def invoke_charter() -> str:
    """
    Invoke the Chart Maker Lambda to create portfolio visualizations.
    The Charter agent will create charts and save them to the database.
    
    Returns:
        Confirmation message
    """
    global current_job_id, current_portfolio_data
    
    # Prepare portfolio data for charter
    portfolio_summary = {
        'total_value': 0,
        'positions': []
    }
    
    if current_portfolio_data:
        for account in current_portfolio_data.get('accounts', []):
            portfolio_summary['total_value'] += account.get('cash_balance', 0)
            for position in account.get('positions', []):
                instrument = position.get('instrument', {})
                portfolio_summary['positions'].append({
                    'symbol': position.get('symbol'),
                    'quantity': position.get('quantity'),
                    'current_price': instrument.get('current_price', 100),
                    'allocation_asset_class': instrument.get('allocation_asset_class', {}),
                    'allocation_regions': instrument.get('allocation_regions', {}),
                    'allocation_sectors': instrument.get('allocation_sectors', {})
                })
    
    result = await invoke_lambda_agent(
        "Charter",
        CHARTER_FUNCTION,
        {
            'job_id': current_job_id,
            'portfolio_data': portfolio_summary
        }
    )
    
    if 'error' in result:
        return f"Charter agent failed: {result['error']}"
    
    return "Charter agent completed successfully. Portfolio visualizations have been created and saved."


@function_tool
async def invoke_retirement() -> str:
    """
    Invoke the Retirement Specialist Lambda for retirement projections.
    The Retirement agent will calculate projections and save them to the database.
    
    Returns:
        Confirmation message
    """
    global current_job_id
    
    result = await invoke_lambda_agent(
        "Retirement",
        RETIREMENT_FUNCTION,
        {'job_id': current_job_id}
    )
    
    if 'error' in result:
        return f"Retirement agent failed: {result['error']}"
    
    return "Retirement agent completed successfully. Retirement projections have been calculated and saved."


@function_tool
async def finalize_job(summary: str, key_findings: List[str], recommendations: List[str]) -> str:
    """
    Finalize the job with the orchestrator's summary and mark it as completed.
    
    Args:
        summary: Executive summary of the analysis
        key_findings: List of key findings from all agents
        recommendations: List of actionable recommendations
        
    Returns:
        Confirmation message
    """
    global current_job_id
    
    try:
        # Save the orchestrator's summary to the database
        summary_payload = {
            'summary': summary,
            'key_findings': key_findings,
            'recommendations': recommendations,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        rows_updated = db.jobs.update_summary(
            job_id=current_job_id,
            summary_payload=summary_payload
        )
        
        # Mark job as completed
        db.jobs.update_status(
            job_id=current_job_id,
            status='completed'
        )
        
        logger.info(f"Job {current_job_id} finalized successfully")
        return f"Job {current_job_id} has been finalized and marked as completed."
        
    except Exception as e:
        logger.error(f"Error finalizing job: {e}")
        return f"Failed to finalize job: {str(e)}"


async def handle_missing_instruments(job_id: str) -> None:
    """
    Check for and tag any instruments missing allocation data.
    This is done automatically before the agent runs.
    """
    logger.info("Checking for instruments missing allocation data...")
    
    # Get job and portfolio data
    job = db.jobs.find_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    user_id = job['clerk_user_id']
    accounts = db.accounts.find_by_user(user_id)
    
    missing = []
    for account in accounts:
        positions = db.positions.find_by_account(account['id'])
        for position in positions:
            instrument = db.instruments.find_by_symbol(position['symbol'])
            if instrument:
                has_allocations = bool(
                    instrument.get('allocation_regions') and 
                    instrument.get('allocation_sectors') and
                    instrument.get('allocation_asset_class')
                )
                if not has_allocations:
                    missing.append({
                        'symbol': position['symbol'],
                        'name': instrument.get('name', '')
                    })
            else:
                missing.append({
                    'symbol': position['symbol'],
                    'name': ''
                })
    
    if missing:
        logger.info(f"Found {len(missing)} instruments needing classification: {[m['symbol'] for m in missing]}")
        
        try:
            response = lambda_client.invoke(
                FunctionName=TAGGER_FUNCTION,
                InvocationType='RequestResponse',
                Payload=json.dumps({'instruments': missing})
            )
            
            result = json.loads(response['Payload'].read())
            
            if isinstance(result, dict) and 'statusCode' in result:
                if result['statusCode'] == 200:
                    logger.info(f"InstrumentTagger completed: Tagged {len(missing)} instruments")
                else:
                    logger.error(f"InstrumentTagger failed with status {result['statusCode']}")
            
        except Exception as e:
            logger.error(f"Error tagging instruments: {e}")
            # Continue anyway - tagging is helpful but not critical
    else:
        logger.info("All instruments have allocation data")


async def load_portfolio_summary(job_id: str) -> Dict[str, Any]:
    """Load portfolio summary data for the agent."""
    try:
        job = db.jobs.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        user_id = job['clerk_user_id']
        user = db.users.find_by_clerk_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        accounts = db.accounts.find_by_user(user_id)
        
        portfolio_data = {
            'user_id': user_id,
            'job_id': job_id,
            'years_until_retirement': user.get('years_until_retirement', 30),
            'target_retirement_income': float(user.get('target_retirement_income', 80000)),
            'accounts': []
        }
        
        for account in accounts:
            positions = db.positions.find_by_account(account['id'])
            account_data = {
                'id': account['id'],
                'name': account['account_name'],
                'cash_balance': float(account.get('cash_balance', 0)),
                'positions': []
            }
            
            for position in positions:
                instrument = db.instruments.find_by_symbol(position['symbol'])
                position_data = {
                    'symbol': position['symbol'],
                    'quantity': float(position['quantity']),
                    'instrument': instrument if instrument else {}
                }
                account_data['positions'].append(position_data)
            
            portfolio_data['accounts'].append(account_data)
        
        return portfolio_data
        
    except Exception as e:
        logger.error(f"Error loading portfolio data: {e}")
        raise


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    before_sleep=lambda retry_state: logger.info(f"Rate limited, waiting {retry_state.next_action.sleep} seconds...")
)
async def run_agent_with_retry(agent, task, max_turns=20):
    """Run agent with retry logic for rate limits."""
    return await Runner.run(agent, input=task, max_turns=max_turns)


async def run_orchestrator(job_id: str) -> None:
    """
    Run the orchestrator agent to coordinate portfolio analysis.
    """
    global current_job_id, current_portfolio_data
    current_job_id = job_id
    
    # Load portfolio data
    current_portfolio_data = await load_portfolio_summary(job_id)
    
    # Handle missing instruments first
    await handle_missing_instruments(job_id)
    
    # Initialize the model with proper region handling
    model_id = f"bedrock/{BEDROCK_MODEL_ID}"
    logger.info(f"Using Bedrock model: {model_id} in region {BEDROCK_REGION}")
    
    # Set AWS region for Bedrock (LiteLLM uses environment variables)
    if BEDROCK_REGION:
        os.environ['AWS_REGION'] = BEDROCK_REGION
        os.environ['AWS_DEFAULT_REGION'] = BEDROCK_REGION
    
    # Create model
    model = LitellmModel(model=model_id)
    
    # Define tools (no structured output)
    tools = [
        invoke_reporter,
        invoke_charter,
        invoke_retirement,
        finalize_job
    ]
    
    # Create the analysis task
    num_accounts = len(current_portfolio_data['accounts'])
    num_positions = sum(len(acc['positions']) for acc in current_portfolio_data['accounts'])
    
    task = ANALYSIS_REQUEST_TEMPLATE.format(
        job_id=job_id,
        user_id=current_portfolio_data['user_id'],
        num_accounts=num_accounts,
        num_positions=num_positions,
        years_until_retirement=current_portfolio_data['years_until_retirement'],
        target_income=current_portfolio_data['target_retirement_income']
    )
    
    # Run the orchestrator agent WITHOUT structured output
    with trace(f"Portfolio Analysis Job {job_id}"):
        logger.info("Creating agent with tools only (no structured output)...")
        agent = Agent(
            name="Financial Planner Orchestrator",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        logger.info(f"Starting Runner.run with max_turns=20...")
        try:
            result = await run_agent_with_retry(agent, task, max_turns=20)
            logger.info("Orchestrator completed")
        except Exception as e:
            logger.error(f"Failed after retries: {e}")
            raise


async def process_job(job_id: str):
    """Process a single job asynchronously."""
    try:
        logger.info(f"Processing job {job_id}")
        
        # Update job status to running
        db.jobs.update_status(job_id=job_id, status='running')
        
        # Run the orchestrator
        await run_orchestrator(job_id)
        
        logger.info(f"Job {job_id} completed successfully")
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        db.jobs.update_status(
            job_id=job_id,
            status='failed',
            error_message=str(e)
        )


def lambda_handler(event, context):
    """
    Lambda handler for SQS-triggered portfolio analysis.
    """
    try:
        # Process each SQS message
        for record in event['Records']:
            # Parse the message
            message = json.loads(record['body'])
            job_id = message.get('job_id')
            
            if not job_id:
                logger.error("No job_id in SQS message")
                continue
            
            # Process the job
            asyncio.run(process_job(job_id))
                
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Jobs processed'})
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }