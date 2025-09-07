"""
Chart Maker Agent Lambda Handler
Creates visualization data for portfolio analysis using tools.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any

from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel

# Try to load .env file if available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # dotenv not available in Lambda

# Import database client for updating job results
import sys
sys.path.append('/opt/python')  # Lambda layer path
try:
    from src import Database  # In Lambda, the layer will have src package
except ImportError:
    # For local testing with editable install
    try:
        import os
        import sys
        # Add parent path for database package
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from database.src import Database
    except ImportError as e:
        print(f"Failed to import Database: {e}")
        # Mock for testing without database
        Database = None

from templates import CHARTER_INSTRUCTIONS

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment
# Use the inference profile ID from the .env file
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-west-2'))

# Global variables for agent context
current_job_id = None
current_portfolio = None
db = None


def init_database():
    """Initialize database connection"""
    global db
    if not db:
        db = Database()
    return db


def analyze_portfolio(portfolio_data: Dict[str, Any]) -> str:
    """
    Analyze the portfolio to understand its composition and calculate key metrics.
    Returns detailed breakdown of positions, accounts, and calculated allocations.
    """
    result = []
    total_value = 0.0
    position_values = {}
    account_totals = {}
    
    # Calculate position values and totals
    for account in portfolio_data.get('accounts', []):
        account_name = account.get('name', 'Unknown')
        account_type = account.get('type', 'unknown')
        cash = float(account.get('cash_balance', 0))
        
        if account_name not in account_totals:
            account_totals[account_name] = {'value': 0, 'type': account_type, 'positions': []}
        
        account_totals[account_name]['value'] += cash
        total_value += cash
        
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            quantity = float(position.get('quantity', 0))
            instrument = position.get('instrument', {})
            price = float(instrument.get('current_price', 1.0))
            value = quantity * price
            
            position_values[symbol] = position_values.get(symbol, 0) + value
            account_totals[account_name]['value'] += value
            account_totals[account_name]['positions'].append({
                'symbol': symbol,
                'value': value,
                'instrument': instrument
            })
            total_value += value
    
    # Build analysis summary
    result.append("Portfolio Analysis:")
    result.append(f"Total Value: ${total_value:,.2f}")
    result.append(f"Number of Accounts: {len(account_totals)}")
    result.append(f"Number of Positions: {len(position_values)}")
    
    result.append("\nAccount Breakdown:")
    for name, data in account_totals.items():
        pct = (data['value'] / total_value * 100) if total_value > 0 else 0
        result.append(f"  {name} ({data['type']}): ${data['value']:,.2f} ({pct:.1f}%)")
    
    result.append("\nTop Holdings by Value:")
    sorted_positions = sorted(position_values.items(), key=lambda x: x[1], reverse=True)[:10]
    for symbol, value in sorted_positions:
        pct = (value / total_value * 100) if total_value > 0 else 0
        result.append(f"  {symbol}: ${value:,.2f} ({pct:.1f}%)")
    
    # Provide instrument allocation data for the agent to use
    result.append("\nDetailed Instrument Data Available:")
    result.append("Each position has allocation data for:")
    result.append("  - Asset classes (equity, fixed_income, real_estate, commodities, cash)")
    result.append("  - Geographic regions (north_america, europe, asia, etc.)")
    result.append("  - Sectors (technology, healthcare, financials, etc.)")
    result.append("\nYou can aggregate these to create meaningful visualizations.")
    
    return "\n".join(result)


@function_tool
async def create_chart(
    chart_key: str,
    title: str,
    description: str,
    chart_type: str,
    data_points: str
) -> str:
    """
    Create a chart and save it to the database.
    
    Args:
        chart_key: Unique identifier for the chart (e.g., 'asset_allocation', 'geography', 'risk_profile')
        title: Display title for the chart
        description: Brief description of what the chart shows
        chart_type: Type of chart - 'pie', 'bar', 'donut', 'horizontalBar', 'line'
        data_points: JSON array string of data points, each with: name, value, percentage, color
    
    Returns:
        Success or error message
    """
    global current_job_id, db
    
    if not current_job_id:
        return "Error: No job ID available"
    
    try:
        # Parse and validate the data points
        data = json.loads(data_points)
        
        if not isinstance(data, list):
            return "Error: data_points must be a JSON array"
        
        # Validate each data point
        for point in data:
            if not all(k in point for k in ['name', 'value', 'percentage', 'color']):
                return "Error: Each data point must have name, value, percentage, and color"
        
        # Verify percentages sum to approximately 100
        total_pct = sum(point['percentage'] for point in data)
        if abs(total_pct - 100.0) > 1.0:  # Allow 1% tolerance
            # Auto-normalize if close
            if 95 < total_pct < 105:
                for point in data:
                    point['percentage'] = round(point['percentage'] * 100 / total_pct, 2)
            else:
                return f"Warning: Percentages sum to {total_pct:.1f}%, not 100%"
        
        # Build chart structure
        chart_data = {
            'title': title,
            'description': description,
            'type': chart_type,
            'data': data
        }
        
        # Initialize charts collection if needed
        if not hasattr(create_chart, 'charts'):
            create_chart.charts = {}
        
        # Add this chart to our collection
        create_chart.charts[chart_key] = chart_data
        
        # Save all charts to database (this will append/update)
        init_database()
        rows_updated = db.jobs.update_charts(current_job_id, create_chart.charts)
        
        if rows_updated > 0:
            return f"Successfully created and saved {chart_key} chart with {len(data)} data points"
        else:
            return f"Created {chart_key} chart but database update returned no rows"
            
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in data_points - {str(e)}"
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        return f"Error creating chart: {str(e)}"


# Color palette suggestions for the agent
COLOR_PALETTES = {
    'blue_gradient': ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE'],
    'green_gradient': ['#10B981', '#34D399', '#6EE7B7', '#A7F3D0', '#D1FAE5'],
    'warm': ['#F59E0B', '#F97316', '#EF4444', '#DC2626', '#B91C1C'],
    'cool': ['#06B6D4', '#0891B2', '#0E7490', '#155E75', '#164E63'],
    'purple': ['#8B5CF6', '#A78BFA', '#C084FC', '#E9D5FF', '#F3E8FF'],
    'mixed': ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
}


async def run_charter_agent(job_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the Charter agent to generate visualization data"""
    global current_job_id, current_portfolio
    
    current_job_id = job_id
    current_portfolio = portfolio_data
    
    # Clear any previous charts
    create_chart.charts = {}
    
    # Set region for Bedrock if specified
    if BEDROCK_MODEL_REGION != os.getenv('AWS_REGION', 'us-east-1'):
        os.environ["AWS_REGION_NAME"] = BEDROCK_MODEL_REGION
        os.environ["AWS_REGION"] = BEDROCK_MODEL_REGION
        os.environ["AWS_DEFAULT_REGION"] = BEDROCK_MODEL_REGION
    
    # Initialize the model - add us. prefix if not present for inference profile
    model_id = BEDROCK_MODEL_ID
    if not model_id.startswith('us.') and 'anthropic.claude' in model_id:
        model_id = f"us.{model_id}"
    model = LitellmModel(model=f"bedrock/{model_id}")
    
    # Analyze the portfolio upfront
    portfolio_analysis = analyze_portfolio(portfolio_data)
    
    # Define the tools - now just one tool!
    tools = [create_chart]
    
    # Create the task for the agent with the analysis already included
    task = f"""Create insightful visualization charts for this investment portfolio.

{portfolio_analysis}

Raw Portfolio Data (for detailed calculations):
{json.dumps(portfolio_data, indent=2)}

Your task:
1. Based on the portfolio analysis and raw data above, decide what charts would be most valuable
2. Create 4-6 charts that tell a compelling story about the portfolio
3. Use create_chart() for each visualization (each call automatically saves to the database)
4. You can aggregate the allocation data from instruments to create meaningful breakdowns

Chart Guidelines:
- Choose chart types that best represent the data (pie for composition, bar for comparisons, etc.)
- Use meaningful chart keys like 'asset_allocation', 'geographic_exposure', 'sector_breakdown', etc.
- Ensure all percentages in each chart sum to exactly 100%
- Use appropriate colors (you can use hex codes like #3B82F6 for blue, #10B981 for green, etc.)
- Consider these color palettes: {json.dumps(COLOR_PALETTES, indent=2)}

You have flexibility to choose what to visualize, but consider:
- Asset class distribution (stocks vs bonds vs alternatives)
- Geographic diversification
- Sector exposure
- Account type breakdown
- Top holdings concentration
- Risk profile visualization
- Tax-advantaged vs taxable split
- Any other insights that would be valuable

Remember: Each chart needs a clear title, description, type (pie/bar/donut/horizontalBar), and data array with name/value/percentage/color for each point."""
    
    # Run the agent
    with trace("Charter Agent Execution"):
        agent = Agent(
            name="Chart Maker",
            instructions=CHARTER_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        await Runner.run(
            agent,
            input=task,
            max_turns=8  # Enough turns to create 4-6 charts
        )
        
        return {'success': True, 'message': 'Charts generated successfully'}


def lambda_handler(event, context):
    """
    Lambda handler for chart generation.
    
    Expected event structure:
    {
        "job_id": "uuid",
        "portfolio_data": {...}
    }
    """
    try:
        logger.info("Chart Maker Lambda invoked")
        
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        job_id = event.get('job_id')
        portfolio_data = event.get('portfolio_data', {})
        
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No job_id provided'})
            }
        
        if not portfolio_data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No portfolio data provided'})
            }
        
        # Run the agent
        asyncio.run(run_charter_agent(job_id, portfolio_data))
        
        logger.info("Chart generation completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'message': 'Charts generated successfully'})
        }
        
    except Exception as e:
        logger.error(f"Error in charter lambda: {e}")
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