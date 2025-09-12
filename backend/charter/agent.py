"""
Chart Maker Agent - creates visualization data for portfolio analysis.
"""

import os
import json
import logging
import re
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass

from agents import function_tool, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel

from templates import CHARTER_INSTRUCTIONS, create_charter_task

logger = logging.getLogger(__name__)



@dataclass
class CharterContext:
    """Context for the Charter agent"""

    job_id: str
    portfolio_data: Dict[str, Any]
    db: Optional[Any] = None  # Database connection (optional for testing)
    charts: Dict[str, Any] = None  # Accumulate charts during session


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
    for account in portfolio_data.get("accounts", []):
        account_name = account.get("name", "Unknown")
        account_type = account.get("type", "unknown")
        cash = float(account.get("cash_balance", 0))

        if account_name not in account_totals:
            account_totals[account_name] = {"value": 0, "type": account_type, "positions": []}

        account_totals[account_name]["value"] += cash
        total_value += cash

        for position in account.get("positions", []):
            symbol = position.get("symbol")
            quantity = float(position.get("quantity", 0))
            instrument = position.get("instrument", {})
            price = float(instrument.get("current_price", 1.0))
            value = quantity * price

            position_values[symbol] = position_values.get(symbol, 0) + value
            account_totals[account_name]["value"] += value
            account_totals[account_name]["positions"].append(
                {"symbol": symbol, "value": value, "instrument": instrument}
            )
            total_value += value

    # Build analysis summary
    result.append("Portfolio Analysis:")
    result.append(f"Total Value: ${total_value:,.2f}")
    result.append(f"Number of Accounts: {len(account_totals)}")
    result.append(f"Number of Positions: {len(position_values)}")

    result.append("\nAccount Breakdown:")
    for name, data in account_totals.items():
        pct = (data["value"] / total_value * 100) if total_value > 0 else 0
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
    wrapper: RunContextWrapper[CharterContext],
    title: str,
    description: str,
    chart_type: Literal['pie', 'bar', 'donut', 'horizontalBar'],
    names: list[str],
    values: list[float], 
    colors: list[str]
) -> str:
    """
    Create a chart and save it to the database.
    
    Args:
        title: Display title like 'Asset Class Distribution'
        description: Brief description of what the chart shows  
        chart_type: Type of visualization to create
        names: Category names like ['Stocks', 'Bonds', 'Cash']
        values: Dollar values like [65900.0, 14100.0, 4600.0]
        colors: Hex colors like ['#3B82F6', '#10B981', '#EF4444']
    
    The chart_key will be auto-generated from the title.
    Returns success or error message.
    """
    job_id = wrapper.context.job_id
    db = wrapper.context.db

    if not job_id:
        return "Error: No job ID available in context"

    # Validate inputs
    if len(names) != len(values) or len(names) != len(colors):
        return f"Error: Mismatched list lengths - names({len(names)}), values({len(values)}), colors({len(colors)})"
    
    if not names:
        return "Error: Empty data - at least one data point required"
    
    # Validate colors are hex format
    for color in colors:
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return f"Error: Invalid hex color '{color}' - use format like '#3B82F6'"
    
    # Calculate total and percentages
    total_value = sum(values)
    if total_value <= 0:
        return "Error: Total value must be positive"
    
    # Generate chart key from title
    chart_key = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')
    if not chart_key:
        chart_key = f"chart_{len(names)}_items"
    
    # Build data points with calculated percentages
    data_points = []
    for name, value, color in zip(names, values, colors):
        percentage = round((value / total_value) * 100, 2)
        data_points.append({
            "name": name,
            "value": value,
            "percentage": percentage,
            "color": color
        })
    
    # Build chart structure
    chart_data = {
        "title": title,
        "description": description, 
        "type": chart_type,
        "data": data_points
    }
    
    # Add chart to context accumulator
    if wrapper.context.charts is None:
        wrapper.context.charts = {}
    wrapper.context.charts[chart_key] = chart_data
    
    # Save accumulated charts to database
    if db:
        success = db.jobs.update_charts(job_id, wrapper.context.charts)
        
        if success:
            logger.info(f"Charter: Stored chart '{chart_key}' for job {job_id} with {len(data_points)} data points")
            return f"Successfully created and saved '{title}' chart with {len(data_points)} data points"
        else:
            logger.error(f"Charter: Failed to update charts for job {job_id}")
            return "Error: Failed to save chart to database"
    else:
        logger.info(f"Charter: Created chart '{chart_key}' (no database)")
        return f"Successfully created '{title}' chart with {len(data_points)} data points (not saved - no database)"


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db=None):
    """Create the charter agent with tools and context."""

    # Get model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    # Set region for LiteLLM Bedrock calls
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region

    model = LitellmModel(model=f"bedrock/{model_id}")

    # Create context with empty charts dict
    context = CharterContext(job_id=job_id, portfolio_data=portfolio_data, db=db, charts={})

    # Tools
    tools = [create_chart]

    # Analyze the portfolio upfront
    portfolio_analysis = analyze_portfolio(portfolio_data)

    # Create the task using template
    task = create_charter_task(portfolio_analysis, json.dumps(portfolio_data, indent=2))

    return model, tools, task, context
