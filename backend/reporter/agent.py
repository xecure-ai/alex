"""
Report Writer Agent - generates portfolio analysis narratives.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from agents import function_tool
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger(__name__)

def calculate_portfolio_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate basic portfolio metrics."""
    metrics = {
        'total_value': 0,
        'cash_balance': 0,
        'num_accounts': len(portfolio_data.get('accounts', [])),
        'num_positions': 0,
        'unique_symbols': set()
    }
    
    for account in portfolio_data.get('accounts', []):
        metrics['cash_balance'] += float(account.get('cash_balance', 0))
        positions = account.get('positions', [])
        metrics['num_positions'] += len(positions)
        
        for position in positions:
            symbol = position.get('symbol')
            if symbol:
                metrics['unique_symbols'].add(symbol)
            
            # Calculate value if we have price
            instrument = position.get('instrument', {})
            if instrument.get('current_price'):
                value = float(position.get('quantity', 0)) * float(instrument['current_price'])
                metrics['total_value'] += value
    
    metrics['total_value'] += metrics['cash_balance']
    metrics['unique_symbols'] = len(metrics['unique_symbols'])
    
    return metrics

def format_portfolio_for_analysis(portfolio_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
    """Format portfolio data for agent analysis."""
    metrics = calculate_portfolio_metrics(portfolio_data)
    
    lines = [
        f"Portfolio Overview:",
        f"- {metrics['num_accounts']} accounts",
        f"- {metrics['num_positions']} total positions",
        f"- {metrics['unique_symbols']} unique holdings",
        f"- ${metrics['cash_balance']:,.2f} in cash",
        f"- ${metrics['total_value']:,.2f} total value" if metrics['total_value'] > 0 else "",
        "",
        "Account Details:"
    ]
    
    for account in portfolio_data.get('accounts', []):
        name = account.get('name', 'Unknown')
        cash = float(account.get('cash_balance', 0))
        lines.append(f"\n{name} (${cash:,.2f} cash):")
        
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            quantity = float(position.get('quantity', 0))
            instrument = position.get('instrument', {})
            name = instrument.get('name', '')
            
            # Include allocation info if available
            allocations = []
            if instrument.get('asset_class'):
                allocations.append(f"Asset: {instrument['asset_class']}")
            if instrument.get('regions'):
                regions = ', '.join([f"{r['name']} {r['percentage']}%" for r in instrument['regions'][:2]])
                allocations.append(f"Regions: {regions}")
            
            alloc_str = f" ({', '.join(allocations)})" if allocations else ""
            lines.append(f"  - {symbol}: {quantity:,.2f} shares{alloc_str}")
    
    # Add user context
    lines.extend([
        "",
        "User Profile:",
        f"- Years to retirement: {user_data.get('years_until_retirement', 'Not specified')}",
        f"- Target retirement income: ${user_data.get('target_retirement_income', 0):,.0f}/year"
    ])
    
    return '\n'.join(lines)

@function_tool
async def update_job_report(job_id: str, report_content: str) -> str:
    """
    Store the generated portfolio analysis report in the database.
    
    Args:
        job_id: The job ID to update
        report_content: The markdown-formatted analysis report
    
    Returns:
        Success confirmation message
    """
    try:
        import sys
        import os
        
        # Add database package to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from database.src.db_client import DatabaseClient
        from database.src.models import JobUpdate
        
        db = DatabaseClient()
        
        # Update job with report
        update = JobUpdate(
            report_payload={
                'content': report_content,
                'generated_at': datetime.utcnow().isoformat(),
                'agent': 'reporter'
            }
        )
        
        success = await db.update_job(job_id, update)
        
        if success:
            logger.info(f"Stored report for job {job_id}")
            return f"Successfully stored the analysis report for job {job_id}"
        else:
            logger.error(f"Failed to update job {job_id}")
            return f"Failed to store report for job {job_id}"
            
    except Exception as e:
        logger.error(f"Error updating job report: {e}")
        return f"Error storing report: {str(e)}"

@function_tool
async def get_market_insights(symbols: List[str]) -> str:
    """
    Retrieve market insights from S3 Vectors knowledge base.
    
    Args:
        symbols: List of symbols to get insights for
    
    Returns:
        Relevant market context and insights
    """
    try:
        import boto3
        
        # Get account ID
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        bucket = f"alex-vectors-{account_id}"
        
        # Get embeddings
        sagemaker = boto3.client('sagemaker-runtime')
        endpoint_name = os.getenv('SAGEMAKER_ENDPOINT', 'alex-embedding-endpoint')
        query = f"market analysis {' '.join(symbols[:5])}" if symbols else "market outlook"
        
        response = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps({'inputs': query})
        )
        
        result = json.loads(response['Body'].read().decode())
        # Extract embedding (handle nested arrays)
        if isinstance(result, list) and result:
            embedding = result[0][0] if isinstance(result[0], list) else result[0]
        else:
            embedding = result
        
        # Search vectors
        s3v = boto3.client('s3vectors')
        response = s3v.query_vectors(
            vectorBucketName=bucket,
            indexName='financial-research',
            queryVector={'float32': embedding},
            topK=3,
            returnMetadata=True
        )
        
        # Format insights
        insights = []
        for vector in response.get('vectors', []):
            metadata = vector.get('metadata', {})
            text = metadata.get('text', '')[:200]
            if text:
                company = metadata.get('company_name', '')
                prefix = f"{company}: " if company else "- "
                insights.append(f"{prefix}{text}...")
        
        if insights:
            return "Market Insights:\n" + "\n".join(insights)
        else:
            return "Market insights unavailable - proceeding with standard analysis."
            
    except Exception as e:
        logger.warning(f"Could not retrieve market insights: {e}")
        return "Market insights unavailable - proceeding with standard analysis."

def create_agent(job_id: str):
    """Create the reporter agent with tools."""
    
    # Get model configuration
    model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-7-sonnet-20250219-v1:0')
    # Add us. prefix for inference profile if not already present
    if not model_id.startswith('us.') and 'anthropic.claude' in model_id:
        model_id = f"us.{model_id}"
    region = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-east-1'))
    
    # Set region if needed
    if region != os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = region
        os.environ['AWS_DEFAULT_REGION'] = region
    
    model = LitellmModel(model=f"bedrock/{model_id}")
    
    # Bind job_id to the update tool
    async def update_report(report_content: str) -> str:
        """Store the generated portfolio analysis report in the database."""
        return await update_job_report(job_id, report_content)
    
    update_report.__name__ = "update_report"
    
    tools = [
        function_tool(update_report),
        get_market_insights
    ]
    
    return model, tools