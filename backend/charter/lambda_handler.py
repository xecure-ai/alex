"""
Chart Maker Agent Lambda Handler
Creates visualization data for portfolio analysis.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from collections import defaultdict

from pydantic import BaseModel, Field, field_validator
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

from templates import CHARTER_INSTRUCTIONS, CHART_GENERATION_TEMPLATE

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-east-1'))

class ChartDataPoint(BaseModel):
    """Individual data point for charts"""
    name: str = Field(description="Label for the data point")
    value: float = Field(description="Numeric value")
    percentage: float = Field(description="Percentage of total")
    color: str = Field(description="Color hex code for visualization")

class ChartConfig(BaseModel):
    """Configuration for a chart"""
    title: str = Field(description="Chart title")
    description: str = Field(description="Brief description of what the chart shows")
    type: str = Field(description="Chart type: pie, bar, donut, horizontalBar")
    data: List[ChartDataPoint] = Field(description="Data points for the chart")
    
    @field_validator('data')
    def validate_percentages(cls, v):
        """Ensure percentages sum to approximately 100"""
        total = sum(point.percentage for point in v)
        if abs(total - 100.0) > 0.1:  # Allow 0.1% tolerance for rounding
            # Normalize to exactly 100%
            for point in v:
                point.percentage = (point.percentage / total) * 100
        return v

class PortfolioCharts(BaseModel):
    """Complete set of portfolio visualization data"""
    asset_class_distribution: ChartConfig = Field(description="Asset class allocation chart")
    geographic_allocation: ChartConfig = Field(description="Geographic distribution chart")
    sector_breakdown: ChartConfig = Field(description="Sector allocation chart")
    account_distribution: ChartConfig = Field(description="Account types distribution chart")
    top_holdings: ChartConfig = Field(description="Top 10 holdings chart")

def analyze_portfolio_allocations(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze portfolio to extract allocation data."""
    
    allocations = {
        'asset_classes': defaultdict(float),
        'regions': defaultdict(float),
        'sectors': defaultdict(float),
        'accounts': defaultdict(float),
        'positions': defaultdict(float),
        'total_positions': 0
    }
    
    # Process each account
    for account in portfolio_data.get('accounts', []):
        account_name = account.get('name', 'Unknown')
        
        # Track cash as an asset class
        cash = account.get('cash_balance', 0)
        if cash > 0:
            allocations['asset_classes']['Cash'] += 1
            allocations['accounts'][account_name] += 1
        
        # Process positions
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            quantity = position.get('quantity', 0)
            
            # Track position sizes (we don't have prices, so use quantity as proxy)
            allocations['positions'][symbol] += quantity
            allocations['total_positions'] += 1
            
            # Get instrument data if available
            instrument = position.get('instrument', {})
            
            # Asset class allocations
            asset_class_alloc = instrument.get('allocation_asset_class', {})
            if asset_class_alloc:
                for asset_class, pct in asset_class_alloc.items():
                    allocations['asset_classes'][asset_class] += pct / 100.0
            else:
                # Default to equity if no data
                allocations['asset_classes']['Equity'] += 1
            
            # Regional allocations
            region_alloc = instrument.get('allocation_regions', {})
            if region_alloc:
                for region, pct in region_alloc.items():
                    allocations['regions'][region] += pct / 100.0
            else:
                # Default to North America if no data
                allocations['regions']['north_america'] += 1
            
            # Sector allocations
            sector_alloc = instrument.get('allocation_sectors', {})
            if sector_alloc:
                for sector, pct in sector_alloc.items():
                    allocations['sectors'][sector] += pct / 100.0
            else:
                # Default to diversified if no data
                allocations['sectors']['diversified'] += 1
            
            # Account distribution (simple count-based)
            allocations['accounts'][account_name] += 1
    
    return allocations

def create_chart_data(allocations: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Convert allocations to chart-ready data."""
    
    charts = {}
    
    # Color schemes for different chart types
    colors = {
        'asset_classes': ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'],
        'regions': ['#6366F1', '#14B8A6', '#F97316', '#EC4899', '#84CC16'],
        'sectors': ['#0EA5E9', '#22C55E', '#FCD34D', '#F87171', '#A78BFA'],
        'accounts': ['#06B6D4', '#34D399', '#FBBF24', '#FB7185', '#C084FC']
    }
    
    # Asset Class Distribution
    asset_total = sum(allocations['asset_classes'].values()) or 1
    charts['asset_classes'] = []
    for i, (asset_class, value) in enumerate(allocations['asset_classes'].items()):
        charts['asset_classes'].append({
            'name': asset_class.replace('_', ' ').title(),
            'value': round(value, 2),
            'percentage': round((value / asset_total) * 100, 2),
            'color': colors['asset_classes'][i % len(colors['asset_classes'])]
        })
    
    # Geographic Allocation
    region_total = sum(allocations['regions'].values()) or 1
    charts['regions'] = []
    for i, (region, value) in enumerate(allocations['regions'].items()):
        charts['regions'].append({
            'name': region.replace('_', ' ').title(),
            'value': round(value, 2),
            'percentage': round((value / region_total) * 100, 2),
            'color': colors['regions'][i % len(colors['regions'])]
        })
    
    # Sector Breakdown
    sector_total = sum(allocations['sectors'].values()) or 1
    charts['sectors'] = []
    for i, (sector, value) in enumerate(allocations['sectors'].items()):
        charts['sectors'].append({
            'name': sector.replace('_', ' ').title(),
            'value': round(value, 2),
            'percentage': round((value / sector_total) * 100, 2),
            'color': colors['sectors'][i % len(colors['sectors'])]
        })
    
    # Account Distribution
    account_total = sum(allocations['accounts'].values()) or 1
    charts['accounts'] = []
    for i, (account, value) in enumerate(allocations['accounts'].items()):
        charts['accounts'].append({
            'name': account,
            'value': round(value, 2),
            'percentage': round((value / account_total) * 100, 2),
            'color': colors['accounts'][i % len(colors['accounts'])]
        })
    
    # Top Holdings (top 10 by quantity)
    sorted_positions = sorted(allocations['positions'].items(), key=lambda x: x[1], reverse=True)[:10]
    position_total = sum(v for _, v in sorted_positions) or 1
    charts['top_holdings'] = []
    for i, (symbol, quantity) in enumerate(sorted_positions):
        charts['top_holdings'].append({
            'name': symbol,
            'value': round(quantity, 2),
            'percentage': round((quantity / position_total) * 100, 2),
            'color': colors['asset_classes'][i % len(colors['asset_classes'])]
        })
    
    return charts

async def generate_charts(portfolio_data: Dict[str, Any]) -> PortfolioCharts:
    """Generate chart configurations using AI."""
    
    # Set region for Bedrock if specified
    if BEDROCK_MODEL_REGION != os.getenv('AWS_REGION', 'us-east-1'):
        os.environ["AWS_REGION_NAME"] = BEDROCK_MODEL_REGION
        os.environ["AWS_REGION"] = BEDROCK_MODEL_REGION
        os.environ["AWS_DEFAULT_REGION"] = BEDROCK_MODEL_REGION
    
    # Initialize the model
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Analyze portfolio allocations
    allocations = analyze_portfolio_allocations(portfolio_data)
    
    # Create chart data
    chart_data = create_chart_data(allocations)
    
    # Build portfolio summary for the agent
    portfolio_summary = f"""
Portfolio Summary:
- Accounts: {len(portfolio_data.get('accounts', []))}
- Total Positions: {allocations['total_positions']}
- Unique Holdings: {len(allocations['positions'])}

Pre-calculated Chart Data:
{json.dumps(chart_data, indent=2)}
"""
    
    # Create the chart generation task
    task = CHART_GENERATION_TEMPLATE.format(
        portfolio_data=portfolio_summary
    )
    
    # Run the charter agent
    with trace("Portfolio Charts Generation"):
        agent = Agent(
            name="Chart Maker",
            instructions=CHARTER_INSTRUCTIONS,
            model=model,
            output_type=PortfolioCharts
        )
        
        result = await Runner.run(
            agent,
            input=task,
            max_turns=5
        )
        
        return result.final_output_as(PortfolioCharts)

def lambda_handler(event, context):
    """
    Lambda handler for chart generation.
    
    Expected event structure:
    {
        "portfolio_data": {...}
    }
    """
    try:
        logger.info("Chart Maker Lambda invoked")
        
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        portfolio_data = event.get('portfolio_data', {})
        
        if not portfolio_data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No portfolio data provided'})
            }
        
        # Generate the charts
        charts = asyncio.run(generate_charts(portfolio_data))
        
        # Convert to dictionary format
        charts_dict = {
            'asset_class_distribution': {
                'title': charts.asset_class_distribution.title,
                'description': charts.asset_class_distribution.description,
                'type': charts.asset_class_distribution.type,
                'data': [point.model_dump() for point in charts.asset_class_distribution.data]
            },
            'geographic_allocation': {
                'title': charts.geographic_allocation.title,
                'description': charts.geographic_allocation.description,
                'type': charts.geographic_allocation.type,
                'data': [point.model_dump() for point in charts.geographic_allocation.data]
            },
            'sector_breakdown': {
                'title': charts.sector_breakdown.title,
                'description': charts.sector_breakdown.description,
                'type': charts.sector_breakdown.type,
                'data': [point.model_dump() for point in charts.sector_breakdown.data]
            },
            'account_distribution': {
                'title': charts.account_distribution.title,
                'description': charts.account_distribution.description,
                'type': charts.account_distribution.type,
                'data': [point.model_dump() for point in charts.account_distribution.data]
            },
            'top_holdings': {
                'title': charts.top_holdings.title,
                'description': charts.top_holdings.description,
                'type': charts.top_holdings.type,
                'data': [point.model_dump() for point in charts.top_holdings.data]
            }
        }
        
        logger.info("Chart generation completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'charts': charts_dict
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
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
            "accounts": [
                {
                    "id": "acc1",
                    "name": "401(k)",
                    "cash_balance": 5000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "allocation_asset_class": {"equity": 100},
                                "allocation_regions": {"north_america": 100},
                                "allocation_sectors": {"technology": 30, "healthcare": 15, "financials": 15, "consumer": 40}
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 50,
                            "instrument": {
                                "name": "Vanguard Total Bond Market ETF",
                                "allocation_asset_class": {"fixed_income": 100},
                                "allocation_regions": {"north_america": 100},
                                "allocation_sectors": {"government": 60, "corporate": 40}
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))