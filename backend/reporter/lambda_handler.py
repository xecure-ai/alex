"""
Report Writer Agent Lambda Handler
Generates comprehensive portfolio analysis narratives.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

from templates import REPORTER_INSTRUCTIONS, ANALYSIS_TASK_TEMPLATE

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-east-1'))

class PortfolioReport(BaseModel):
    """Structured portfolio analysis report"""
    executive_summary: str = Field(description="3-4 key points executive summary")
    portfolio_composition: str = Field(description="Detailed portfolio composition analysis")
    diversification_assessment: str = Field(description="Analysis of portfolio diversification")
    risk_evaluation: str = Field(description="Risk profile and exposure analysis")
    retirement_readiness: str = Field(description="Assessment of retirement preparedness")
    recommendations: List[str] = Field(description="5-7 specific, actionable recommendations")
    conclusion: str = Field(description="Brief concluding remarks")

def calculate_portfolio_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate basic portfolio metrics for analysis."""
    metrics = {
        'total_value': 0,
        'cash_balance': 0,
        'invested_value': 0,
        'num_accounts': 0,
        'num_positions': 0,
        'unique_symbols': set()
    }
    
    accounts = portfolio_data.get('accounts', [])
    metrics['num_accounts'] = len(accounts)
    
    for account in accounts:
        cash = account.get('cash_balance', 0)
        metrics['cash_balance'] += cash
        
        positions = account.get('positions', [])
        metrics['num_positions'] += len(positions)
        
        for position in positions:
            metrics['unique_symbols'].add(position.get('symbol'))
            # Note: We don't have prices here, so we can't calculate value
            # The agent will need to work with position counts
    
    metrics['unique_symbols'] = len(metrics['unique_symbols'])
    
    return metrics

def format_portfolio_summary(portfolio_data: Dict[str, Any]) -> str:
    """Format portfolio data into a readable summary."""
    metrics = calculate_portfolio_metrics(portfolio_data)
    
    summary_parts = []
    summary_parts.append(f"Accounts: {metrics['num_accounts']}")
    summary_parts.append(f"Total Positions: {metrics['num_positions']}")
    summary_parts.append(f"Unique Holdings: {metrics['unique_symbols']}")
    summary_parts.append(f"Cash Balance: ${metrics['cash_balance']:,.2f}")
    
    # Add account details
    summary_parts.append("\n\nAccount Breakdown:")
    for account in portfolio_data.get('accounts', []):
        name = account.get('name', 'Unknown Account')
        cash = account.get('cash_balance', 0)
        num_positions = len(account.get('positions', []))
        summary_parts.append(f"- {name}: {num_positions} positions, ${cash:,.2f} cash")
    
    # Add position details
    summary_parts.append("\n\nHoldings:")
    for account in portfolio_data.get('accounts', []):
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            quantity = position.get('quantity')
            instrument = position.get('instrument', {})
            name = instrument.get('name', '')
            if name:
                summary_parts.append(f"- {symbol}: {quantity:,.2f} shares ({name})")
            else:
                summary_parts.append(f"- {symbol}: {quantity:,.2f} shares")
    
    return "\n".join(summary_parts)

def get_market_context(portfolio_symbols: List[str] = None) -> str:
    """
    Get market context from S3 Vectors knowledge base.
    
    Args:
        portfolio_symbols: List of symbols in the portfolio for targeted search
        
    Returns:
        Relevant market context
    """
    try:
        import boto3
        
        # Get account ID for bucket name
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        vectors_bucket = f"alex-vectors-{account_id}"
        
        # Initialize clients
        sagemaker_runtime = boto3.client('sagemaker-runtime')
        s3_vectors = boto3.client('s3vectors')
        
        # Create search query based on portfolio
        if portfolio_symbols:
            # Search for context about specific holdings
            query = f"market analysis {' '.join(portfolio_symbols[:5])}"
        else:
            query = "market outlook equity bonds economy"
        
        # Get embedding
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName='alex-embeddings',
            ContentType='application/json',
            Body=json.dumps({'inputs': query})
        )
        
        result = json.loads(response['Body'].read().decode())
        # Extract embedding from nested array
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], list) and len(result[0]) > 0:
                if isinstance(result[0][0], list):
                    embedding = result[0][0]
                else:
                    embedding = result[0]
            else:
                embedding = result
        else:
            embedding = result
        
        # Search S3 Vectors
        response = s3_vectors.query_vectors(
            vectorBucketName=vectors_bucket,
            indexName='financial-research',
            queryVector={"float32": embedding},
            topK=3,
            returnDistance=True,
            returnMetadata=True
        )
        
        # Format results
        context_parts = ["Current Market Research:"]
        for vector in response.get('vectors', []):
            metadata = vector.get('metadata', {})
            text = metadata.get('text', '')
            if text:
                company = metadata.get('company_name', '')
                if company:
                    context_parts.append(f"\n{company}: {text[:200]}...")
                else:
                    context_parts.append(f"\n- {text[:200]}...")
        
        if len(context_parts) > 1:
            return "\n".join(context_parts)
        else:
            # Fallback to basic context if S3 Vectors is empty
            return """
Current Market Environment:
- Equity markets showing mixed signals
- Interest rate environment remains uncertain
- Technology sector facing regulatory headwinds
- International diversification increasingly important
"""
            
    except Exception as e:
        logger.error(f"Error getting market context from S3 Vectors: {e}")
        # Return fallback context
        return """
Market Context (Note: Live data unavailable):
- Consider current market volatility in allocation decisions
- Diversification across asset classes remains crucial
- Long-term perspective important for retirement planning
"""

async def generate_report(portfolio_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> PortfolioReport:
    """Generate the portfolio analysis report using AI."""
    
    # Set region for Bedrock if specified
    if BEDROCK_MODEL_REGION != os.getenv('AWS_REGION', 'us-east-1'):
        os.environ["AWS_REGION_NAME"] = BEDROCK_MODEL_REGION
        os.environ["AWS_REGION"] = BEDROCK_MODEL_REGION
        os.environ["AWS_DEFAULT_REGION"] = BEDROCK_MODEL_REGION
    
    # Initialize the model
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Format portfolio summary
    portfolio_summary = format_portfolio_summary(portfolio_data)
    
    # Extract portfolio symbols for targeted market research
    portfolio_symbols = []
    for account in portfolio_data.get('accounts', []):
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            if symbol:
                portfolio_symbols.append(symbol)
    
    # Get market context from S3 Vectors
    market_context = get_market_context(portfolio_symbols)
    
    # Create the analysis task
    task = ANALYSIS_TASK_TEMPLATE.format(
        portfolio_data=portfolio_summary,
        years_until_retirement=user_preferences.get('years_until_retirement', 30),
        target_income=user_preferences.get('target_retirement_income', 80000),
        market_context=market_context
    )
    
    # Run the reporter agent
    with trace("Portfolio Report Generation"):
        agent = Agent(
            name="Report Writer",
            instructions=REPORTER_INSTRUCTIONS,
            model=model,
            output_type=PortfolioReport
        )
        
        result = await Runner.run(
            agent,
            input=task,
            max_turns=5
        )
        
        return result.final_output_as(PortfolioReport)

def lambda_handler(event, context):
    """
    Lambda handler for report generation.
    
    Expected event structure:
    {
        "portfolio_data": {...},
        "user_preferences": {
            "years_until_retirement": 30,
            "target_retirement_income": 80000
        }
    }
    """
    try:
        logger.info("Report Writer Lambda invoked")
        
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        portfolio_data = event.get('portfolio_data', {})
        user_preferences = event.get('user_preferences', {})
        
        if not portfolio_data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No portfolio data provided'})
            }
        
        # Generate the report
        report = asyncio.run(generate_report(portfolio_data, user_preferences))
        
        # Format the complete report as markdown
        markdown_report = f"""# Portfolio Analysis Report

## Executive Summary
{report.executive_summary}

## Portfolio Composition
{report.portfolio_composition}

## Diversification Assessment
{report.diversification_assessment}

## Risk Evaluation
{report.risk_evaluation}

## Retirement Readiness
{report.retirement_readiness}

## Recommendations
{chr(10).join(f'- {rec}' for rec in report.recommendations)}

## Conclusion
{report.conclusion}

---
*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*
"""
        
        logger.info("Report generation completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'report': markdown_report,
                'summary': report.executive_summary,
                'recommendations': report.recommendations
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
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
        "portfolio_data": {
            "user_id": "test_user",
            "accounts": [
                {
                    "id": "acc1",
                    "name": "401(k)",
                    "cash_balance": 5000,
                    "positions": [
                        {"symbol": "SPY", "quantity": 100, "instrument": {"name": "SPDR S&P 500 ETF"}},
                        {"symbol": "BND", "quantity": 50, "instrument": {"name": "Vanguard Total Bond Market ETF"}}
                    ]
                }
            ]
        },
        "user_preferences": {
            "years_until_retirement": 25,
            "target_retirement_income": 75000
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))