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

from pydantic import BaseModel, Field, ConfigDict
from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

# Import database package
from src.models import Database
from src.schemas import JobUpdate

from templates import ORCHESTRATOR_INSTRUCTIONS, ANALYSIS_REQUEST_TEMPLATE

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
db = Database()
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-east-1'))
VECTORS_BUCKET = os.getenv('VECTORS_BUCKET', 'alex-vectors')
SAGEMAKER_ENDPOINT = os.getenv('SAGEMAKER_ENDPOINT', 'alex-embeddings')
REGION = os.getenv('AWS_REGION', 'us-east-1')

# Lambda function names from environment
TAGGER_FUNCTION = os.getenv('TAGGER_FUNCTION', 'alex-tagger')
REPORTER_FUNCTION = os.getenv('REPORTER_FUNCTION', 'alex-reporter')
CHARTER_FUNCTION = os.getenv('CHARTER_FUNCTION', 'alex-charter')
RETIREMENT_FUNCTION = os.getenv('RETIREMENT_FUNCTION', 'alex-retirement')

# Structured output models
class AnalysisResult(BaseModel):
    """Complete portfolio analysis result"""
    status: str = Field(description="Status of the analysis: completed or failed")
    summary: str = Field(description="Executive summary of the analysis")
    key_findings: List[str] = Field(description="List of key findings from the analysis")
    recommendations: List[str] = Field(description="List of actionable recommendations")
    error_message: Optional[str] = Field(default=None, description="Error message if analysis failed")

class InstrumentToTag(BaseModel):
    """Instrument that needs tagging"""
    model_config = ConfigDict(extra='forbid')
    
    symbol: str = Field(description="Ticker symbol")
    name: str = Field(default="", description="Instrument name")

class InstrumentInfo(BaseModel):
    """Basic instrument information"""
    model_config = ConfigDict(extra='forbid')
    
    symbol: str = Field(description="Ticker symbol")
    name: str = Field(default="", description="Instrument name")
    has_allocations: bool = Field(default=False, description="Whether allocation data is available")

class PositionInfo(BaseModel):
    """Position information"""
    model_config = ConfigDict(extra='forbid')
    
    symbol: str
    quantity: float
    instrument: Optional[InstrumentInfo] = None

class AccountInfo(BaseModel):
    """Account information"""
    model_config = ConfigDict(extra='forbid')
    
    id: str
    name: str
    cash_balance: float = 0.0
    positions: List[PositionInfo] = Field(default_factory=list)

class UserPreferences(BaseModel):
    """User preferences"""
    model_config = ConfigDict(extra='forbid')
    
    years_until_retirement: int = 30
    target_retirement_income: float = 80000.0

class PortfolioData(BaseModel):
    """Complete portfolio data"""
    model_config = ConfigDict(extra='forbid')
    
    user_id: str
    job_id: str
    user_preferences: UserPreferences
    accounts: List[AccountInfo]

# Helper functions
def get_embedding(text: str) -> List[float]:
    """Get embedding vector from SageMaker endpoint."""
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    
    result = json.loads(response['Body'].read().decode())
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested

# Agent tools
@function_tool
async def check_missing_instruments(portfolio_data: PortfolioData) -> List[InstrumentToTag]:
    """
    Check for instruments missing allocation data.
    
    Args:
        portfolio_data: Portfolio data with accounts and positions
        
    Returns:
        List of instruments that need tagging
    """
    missing = []
    
    for account in portfolio_data.accounts:
        for position in account.positions:
            if position.instrument:
                # Check if instrument has allocation data
                if not position.instrument.has_allocations:
                    missing.append(InstrumentToTag(
                        symbol=position.symbol,
                        name=position.instrument.name
                    ))
            else:
                # No instrument data at all
                missing.append(InstrumentToTag(
                    symbol=position.symbol,
                    name=""
                ))
    
    return missing

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
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        # Unwrap Lambda response if it has the standard format
        if isinstance(result, dict) and 'statusCode' in result and 'body' in result:
            # Parse the body if it's a JSON string
            if isinstance(result['body'], str):
                try:
                    result = json.loads(result['body'])
                except json.JSONDecodeError:
                    # If body is not JSON, return as is
                    result = {'message': result['body']}
            else:
                result = result['body']
        
        logger.info(f"{agent_name} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error invoking {agent_name}: {e}")
        return {'error': str(e)}

@function_tool
async def invoke_tagger(instruments: List[InstrumentToTag]) -> Dict[str, Any]:
    """
    Invoke the InstrumentTagger Lambda to classify instruments.
    
    Args:
        instruments: List of instruments to tag
        
    Returns:
        Tagging results dictionary
    """
    result = await invoke_lambda_agent(
        "InstrumentTagger",
        TAGGER_FUNCTION,
        {'instruments': [inst.model_dump() for inst in instruments]}
    )
    return result

@function_tool
async def invoke_reporter(portfolio_data: PortfolioData) -> Dict[str, Any]:
    """
    Invoke the Report Writer Lambda to generate analysis narrative.
    
    Args:
        portfolio_data: Complete portfolio data
        
    Returns:
        Report generation results dictionary
    """
    result = await invoke_lambda_agent(
        "Report Writer",
        REPORTER_FUNCTION,
        {
            'portfolio_data': portfolio_data.model_dump(),
            'user_preferences': portfolio_data.user_preferences.model_dump()
        }
    )
    return result

@function_tool
async def invoke_charter(portfolio_data: PortfolioData) -> Dict[str, Any]:
    """
    Invoke the Chart Maker Lambda to create visualizations.
    
    Args:
        portfolio_data: Complete portfolio data
        
    Returns:
        Chart data dictionary in Recharts format
    """
    result = await invoke_lambda_agent(
        "Chart Maker",
        CHARTER_FUNCTION,
        {'portfolio_data': portfolio_data.model_dump()}
    )
    return result

@function_tool
async def invoke_retirement(portfolio_data: PortfolioData) -> Dict[str, Any]:
    """
    Invoke the Retirement Specialist Lambda for projections.
    
    Args:
        portfolio_data: Complete portfolio data with user retirement goals
        
    Returns:
        Retirement analysis and projections dictionary
    """
    result = await invoke_lambda_agent(
        "Retirement Specialist",
        RETIREMENT_FUNCTION,
        {
            'portfolio_data': portfolio_data.model_dump(),
            'user_preferences': portfolio_data.user_preferences.model_dump()
        }
    )
    return result

@function_tool
async def search_market_knowledge(query: str, k: int = 5) -> str:
    """
    Search the S3 Vectors knowledge base for relevant market research.
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        Relevant market context and insights
    """
    try:
        # Get embedding for query
        query_embedding = get_embedding(query)
        
        # Get the correct bucket name with account ID
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        vectors_bucket = f"alex-vectors-{account_id}"
        
        # Search S3 Vectors using boto3
        s3_vectors = boto3.client('s3vectors')
        response = s3_vectors.query_vectors(
            vectorBucketName=vectors_bucket,
            indexName='financial-research',
            queryVector={"float32": query_embedding},
            topK=k,
            returnDistance=True,
            returnMetadata=True
        )
        
        # Format results into context
        context_parts = []
        for vector in response.get('vectors', [])[:3]:  # Top 3 most relevant
            metadata = vector.get('metadata', {})
            text = metadata.get('text', '')
            if text:
                # Include company context if available
                company = metadata.get('company_name', '')
                ticker = metadata.get('ticker', '')
                if company or ticker:
                    context_parts.append(f"[{company} ({ticker})]: {text}")
                else:
                    context_parts.append(text)
        
        if context_parts:
            return "Relevant market research:\n\n" + "\n\n".join(context_parts)
        else:
            return "No relevant market context found in knowledge base."
            
    except Exception as e:
        logger.error(f"Error retrieving market context: {e}")
        # Return gracefully - don't fail the entire analysis
        return f"Market research unavailable (S3 Vectors error: {str(e)})"

async def update_job_status(job_id: str, status: str, result_json: Optional[str] = None, error_message: Optional[str] = None) -> bool:
    """
    Update the job status in the database (direct call version).
    
    Args:
        job_id: Job ID to update
        status: New status (running, completed, failed)
        result_json: JSON string of results if completed
        error_message: Error message if failed
        
    Returns:
        Success boolean
    """
    try:
        # Parse result JSON if provided
        result_data = None
        if result_json:
            result_data = json.loads(result_json)
        
        # Use the Jobs model's update_status method
        rows_updated = db.jobs.update_status(
            job_id=job_id,
            status=status,
            result_payload=result_data,
            error_message=error_message
        )
        return rows_updated > 0
        
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        return False

@function_tool  
async def update_job_status_tool(job_id: str, status: str, result_json: Optional[str] = None, error_message: Optional[str] = None) -> bool:
    """
    Update the job status in the database (agent tool version).
    
    Args:
        job_id: Job ID to update
        status: New status (running, completed, failed)
        result_json: JSON string of results if completed
        error_message: Error message if failed
        
    Returns:
        Success boolean
    """
    return await update_job_status(job_id, status, result_json, error_message)

async def load_portfolio_data(job_id: str) -> PortfolioData:
    """Load portfolio data for a job from the database."""
    try:
        # Get job details
        job = db.jobs.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        user_id = job['clerk_user_id']
        
        # Get user preferences
        user = db.users.find_by_clerk_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Build user preferences
        user_prefs = UserPreferences(
            years_until_retirement=user.get('years_until_retirement', 30),
            target_retirement_income=float(user.get('target_retirement_income', 80000))
        )
        
        # Get accounts and positions
        accounts = db.accounts.find_by_user(user_id)
        account_list = []
        
        for account in accounts:
            positions = db.positions.find_by_account(account['id'])
            position_list = []
            
            for position in positions:
                # Get instrument details
                instrument_data = db.instruments.find_by_symbol(position['symbol'])
                
                instrument_info = None
                if instrument_data:
                    has_allocs = bool(
                        instrument_data.get('allocation_regions') and 
                        instrument_data.get('allocation_sectors') and
                        instrument_data.get('allocation_asset_class')
                    )
                    instrument_info = InstrumentInfo(
                        symbol=instrument_data['symbol'],
                        name=instrument_data.get('name', ''),
                        has_allocations=has_allocs
                    )
                
                position_list.append(PositionInfo(
                    symbol=position['symbol'],
                    quantity=float(position['quantity']),
                    instrument=instrument_info
                ))
            
            account_list.append(AccountInfo(
                id=account['id'],
                name=account['account_name'],
                cash_balance=float(account.get('cash_balance', 0)),
                positions=position_list
            ))
        
        return PortfolioData(
            user_id=user_id,
            job_id=job_id,
            user_preferences=user_prefs,
            accounts=account_list
        )
        
    except Exception as e:
        logger.error(f"Error loading portfolio data: {e}")
        raise

async def run_orchestrator(portfolio_data: PortfolioData) -> AnalysisResult:
    """
    Run the orchestrator agent to coordinate portfolio analysis.
    """
    # Set region for Bedrock if different from default
    if BEDROCK_MODEL_REGION != REGION:
        os.environ["AWS_REGION_NAME"] = BEDROCK_MODEL_REGION
        os.environ["AWS_REGION"] = BEDROCK_MODEL_REGION
        os.environ["AWS_DEFAULT_REGION"] = BEDROCK_MODEL_REGION
    
    # Initialize the model
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Define available tools
    tools = [
        check_missing_instruments,
        invoke_tagger,
        invoke_reporter,
        invoke_charter,
        invoke_retirement,
        search_market_knowledge,
        update_job_status_tool
    ]
    
    # Create the analysis task
    task = ANALYSIS_REQUEST_TEMPLATE.format(
        user_id=portfolio_data.user_id,
        portfolio_data=json.dumps(portfolio_data.model_dump(), indent=2, default=str),
        years_until_retirement=portfolio_data.user_preferences.years_until_retirement,
        target_income=portfolio_data.user_preferences.target_retirement_income
    )
    
    # Run the orchestrator agent
    with trace(f"Portfolio Analysis Job {portfolio_data.job_id}"):
        agent = Agent(
            name="Financial Planner Orchestrator",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            model=model,
            tools=tools,
            output_type=AnalysisResult
        )
        
        result = await Runner.run(
            agent,
            input=task,
            max_turns=20
        )
        
        return result.final_output_as(AnalysisResult)

async def process_job(job_id: str):
    """Process a single job asynchronously."""
    try:
        logger.info(f"Processing job {job_id}")
        
        # Update job status to running
        await update_job_status(job_id, 'running')
        
        # Load portfolio data
        portfolio_data = await load_portfolio_data(job_id)
        
        # Run the orchestrator
        result = await run_orchestrator(portfolio_data)
        
        # Update job with results
        if result.status == 'completed':
            result_json = json.dumps({
                'summary': result.summary,
                'key_findings': result.key_findings,
                'recommendations': result.recommendations
            })
            await update_job_status(
                job_id,
                'completed',
                result_json=result_json
            )
            logger.info(f"Job {job_id} completed successfully")
        else:
            await update_job_status(
                job_id,
                'failed',
                error_message=result.error_message
            )
            logger.error(f"Job {job_id} failed: {result.error_message}")
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        await update_job_status(
            job_id,
            'failed',
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
            
            # Process the job in a single async context
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