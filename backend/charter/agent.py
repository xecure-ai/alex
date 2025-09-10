"""
Chart Maker Agent - creates visualization data for portfolio analysis.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from agents import function_tool, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger(__name__)

# Color palette suggestions
COLOR_PALETTES = {
    "blue_gradient": ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"],
    "green_gradient": ["#10B981", "#34D399", "#6EE7B7", "#A7F3D0", "#D1FAE5"],
    "warm": ["#F59E0B", "#F97316", "#EF4444", "#DC2626", "#B91C1C"],
    "cool": ["#06B6D4", "#0891B2", "#0E7490", "#155E75", "#164E63"],
    "purple": ["#8B5CF6", "#A78BFA", "#C084FC", "#E9D5FF", "#F3E8FF"],
    "mixed": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"],
}


@dataclass
class CharterContext:
    """Context for the Charter agent"""

    job_id: str
    portfolio_data: Dict[str, Any]
    db: Optional[Any] = None  # Database connection (optional for testing)


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
    chart_key: str,
    title: str,
    description: str,
    chart_type: str,
    data_points: str,
) -> str:
    """
    Create a chart and save it to the database.

    Args:
        wrapper: Context wrapper with job_id and database
        chart_key: Unique identifier for the chart (e.g., 'asset_allocation', 'geography')
        title: Display title for the chart
        description: Brief description of what the chart shows
        chart_type: Type of chart - 'pie', 'bar', 'donut', 'horizontalBar', 'line'
        data_points: JSON array string of data points, each with: name, value, percentage, color

    Returns:
        Success or error message
    """
    job_id = wrapper.context.job_id
    db = wrapper.context.db

    if not job_id:
        return "Error: No job ID available in context"

    try:
        # Parse and validate the data points
        data = json.loads(data_points)

        if not isinstance(data, list):
            return "Error: data_points must be a JSON array"

        # Validate each data point
        for point in data:
            if not all(k in point for k in ["name", "value", "percentage", "color"]):
                return "Error: Each data point must have name, value, percentage, and color"

        # Verify percentages sum to approximately 100
        total_pct = sum(point["percentage"] for point in data)
        if abs(total_pct - 100.0) > 1.0:  # Allow 1% tolerance
            # Auto-normalize if close
            if 80 < total_pct < 120:
                for point in data:
                    point["percentage"] = round(point["percentage"] * 100 / total_pct, 2)
            else:
                logger.warning(f"Charter: Percentages sum to {total_pct:.1f}%, not 100%")

        # Build chart structure
        chart_data = {"title": title, "description": description, "type": chart_type, "data": data}

        # Initialize charts collection if needed
        if not hasattr(create_chart, "charts"):
            create_chart.charts = {}

        # Add this chart to our collection
        create_chart.charts[chart_key] = chart_data

        # Save all charts to database if available
        if db:
            success = db.jobs.update_charts(job_id, create_chart.charts)

            if success:
                logger.info(f"Charter: Stored chart '{chart_key}' for job {job_id}")
                return (
                    f"Successfully created and saved {chart_key} chart with {len(data)} data points"
                )
            else:
                logger.error(f"Charter: Failed to update charts for job {job_id}")
                return f"Created {chart_key} chart but database update failed"
        else:
            logger.info(f"Charter: Created chart '{chart_key}' (no database)")
            return f"Successfully created {chart_key} chart with {len(data)} data points (not saved - no database)"

    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in data_points - {str(e)}"
    except Exception as e:
        logger.error(f"Charter: Error creating chart: {e}")
        return f"Error creating chart: {str(e)}"


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db=None):
    """Create the charter agent with tools and context."""

    # Get model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    # Set region for LiteLLM Bedrock calls
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region

    model = LitellmModel(model=f"bedrock/{model_id}")

    # Clear any previous charts
    create_chart.charts = {}

    # Create context
    context = CharterContext(job_id=job_id, portfolio_data=portfolio_data, db=db)

    # Tools - just the decorated function!
    tools = [create_chart]

    # Analyze the portfolio upfront
    portfolio_analysis = analyze_portfolio(portfolio_data)

    # Create the task with analysis and color palettes
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

    return model, tools, task, context
