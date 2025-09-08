"""
Retirement Specialist Agent Lambda Handler
Provides retirement planning analysis and projections using tools.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
import random

from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

load_dotenv(override=True)

# Import database client
import sys
sys.path.append('/opt/python')  # Lambda layer path
try:
    from src import Database  # In Lambda, the layer will have src package
except ImportError:
    # For local testing with editable install
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from database.src import Database
    except ImportError as e:
        print(f"Failed to import Database: {e}")
        Database = None

from templates import RETIREMENT_INSTRUCTIONS

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-7-sonnet-20250219-v1:0')
# Add us. prefix for inference profile if not already present
if not BEDROCK_MODEL_ID.startswith('us.') and 'anthropic.claude' in BEDROCK_MODEL_ID:
    BEDROCK_MODEL_ID = f"us.{BEDROCK_MODEL_ID}"
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-west-2'))

# Global variables for agent context
current_job_id = None
db = None


def init_database():
    """Initialize database connection"""
    global db
    if not db and Database:
        db = Database()
    return db


def calculate_portfolio_value(portfolio_data: Dict[str, Any]) -> float:
    """Calculate current portfolio value."""
    total_value = 0.0
    
    for account in portfolio_data.get('accounts', []):
        cash = float(account.get('cash_balance', 0))
        total_value += cash
        
        for position in account.get('positions', []):
            quantity = float(position.get('quantity', 0))
            instrument = position.get('instrument', {})
            price = float(instrument.get('current_price', 100))  # Default price if not available
            total_value += quantity * price
    
    return total_value


def calculate_asset_allocation(portfolio_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate asset allocation percentages."""
    total_equity = 0.0
    total_bonds = 0.0
    total_real_estate = 0.0
    total_commodities = 0.0
    total_cash = 0.0
    total_value = 0.0
    
    for account in portfolio_data.get('accounts', []):
        cash = float(account.get('cash_balance', 0))
        total_cash += cash
        total_value += cash
        
        for position in account.get('positions', []):
            quantity = float(position.get('quantity', 0))
            instrument = position.get('instrument', {})
            price = float(instrument.get('current_price', 100))
            value = quantity * price
            total_value += value
            
            # Get asset class allocation
            asset_allocation = instrument.get('allocation_asset_class', {})
            if asset_allocation:
                total_equity += value * asset_allocation.get('equity', 0) / 100
                total_bonds += value * asset_allocation.get('fixed_income', 0) / 100
                total_real_estate += value * asset_allocation.get('real_estate', 0) / 100
                total_commodities += value * asset_allocation.get('commodities', 0) / 100
                total_cash += value * asset_allocation.get('cash', 0) / 100
            else:
                # Default allocation based on asset class
                asset_class = instrument.get('asset_class', 'equity')
                if asset_class == 'equity':
                    total_equity += value
                elif asset_class == 'fixed_income':
                    total_bonds += value
                else:
                    total_equity += value  # Default to equity
    
    if total_value > 0:
        return {
            'equity': total_equity / total_value,
            'bonds': total_bonds / total_value,
            'real_estate': total_real_estate / total_value,
            'commodities': total_commodities / total_value,
            'cash': total_cash / total_value
        }
    else:
        # Default 60/40 portfolio
        return {
            'equity': 0.6,
            'bonds': 0.4,
            'real_estate': 0.0,
            'commodities': 0.0,
            'cash': 0.0
        }


def run_monte_carlo_simulation(
    current_value: float,
    years_until_retirement: int,
    target_income: float,
    asset_allocation: Dict[str, float],
    num_simulations: int = 500  # Reduced from 1000 for speed
) -> Dict[str, Any]:
    """Run simplified Monte Carlo simulation for retirement planning."""
    
    # Market assumptions
    equity_return_mean = 0.07
    equity_return_std = 0.18
    bond_return_mean = 0.04
    bond_return_std = 0.05
    real_estate_return_mean = 0.06
    real_estate_return_std = 0.12
    inflation_rate = 0.03
    
    successful_scenarios = 0
    final_values = []
    years_lasted = []
    retirement_years = 30  # Assume 30 years in retirement
    
    for _ in range(num_simulations):
        portfolio_value = current_value
        
        # Accumulation phase
        for year in range(years_until_retirement):
            equity_return = random.gauss(equity_return_mean, equity_return_std)
            bond_return = random.gauss(bond_return_mean, bond_return_std)
            real_estate_return = random.gauss(real_estate_return_mean, real_estate_return_std)
            
            portfolio_return = (
                asset_allocation['equity'] * equity_return +
                asset_allocation['bonds'] * bond_return +
                asset_allocation['real_estate'] * real_estate_return +
                asset_allocation['cash'] * 0.02  # Cash return
            )
            
            portfolio_value *= (1 + portfolio_return)
            # Add annual contributions (simplified)
            portfolio_value += 10000  # Assume $10k annual contribution
        
        retirement_start_value = portfolio_value
        
        # Distribution phase
        years_income_lasted = 0
        annual_withdrawal = target_income
        
        for year in range(retirement_years):
            if portfolio_value <= 0:
                break
            
            # Adjust withdrawal for inflation
            annual_withdrawal *= (1 + inflation_rate)
            
            # Market returns during retirement
            equity_return = random.gauss(equity_return_mean, equity_return_std)
            bond_return = random.gauss(bond_return_mean, bond_return_std)
            real_estate_return = random.gauss(real_estate_return_mean, real_estate_return_std)
            
            portfolio_return = (
                asset_allocation['equity'] * equity_return +
                asset_allocation['bonds'] * bond_return +
                asset_allocation['real_estate'] * real_estate_return +
                asset_allocation['cash'] * 0.02
            )
            
            portfolio_value = portfolio_value * (1 + portfolio_return) - annual_withdrawal
            
            if portfolio_value > 0:
                years_income_lasted += 1
        
        final_values.append(max(0, portfolio_value))
        years_lasted.append(years_income_lasted)
        
        if years_income_lasted >= retirement_years:
            successful_scenarios += 1
    
    # Calculate statistics
    final_values.sort()
    success_rate = (successful_scenarios / num_simulations) * 100
    
    # Calculate expected value at retirement using average returns
    expected_return = (
        asset_allocation['equity'] * equity_return_mean +
        asset_allocation['bonds'] * bond_return_mean +
        asset_allocation['real_estate'] * real_estate_return_mean +
        asset_allocation['cash'] * 0.02
    )
    expected_value_at_retirement = current_value
    for _ in range(years_until_retirement):
        expected_value_at_retirement *= (1 + expected_return)
        expected_value_at_retirement += 10000
    
    return {
        'success_rate': round(success_rate, 1),
        'median_final_value': round(final_values[num_simulations // 2], 2),
        'percentile_10': round(final_values[num_simulations // 10], 2),
        'percentile_90': round(final_values[9 * num_simulations // 10], 2),
        'average_years_lasted': round(sum(years_lasted) / len(years_lasted), 1),
        'expected_value_at_retirement': round(expected_value_at_retirement, 2)
    }


def generate_projections(
    current_value: float,
    years_until_retirement: int,
    asset_allocation: Dict[str, float],
    current_age: int
) -> list:
    """Generate simplified retirement projections."""
    
    # Expected returns
    expected_return = (
        asset_allocation['equity'] * 0.07 +
        asset_allocation['bonds'] * 0.04 +
        asset_allocation['real_estate'] * 0.06 +
        asset_allocation['cash'] * 0.02
    )
    
    projections = []
    portfolio_value = current_value
    
    # Only show key milestones (every 5 years)
    milestone_years = list(range(0, years_until_retirement + 31, 5))
    
    for year in milestone_years:
        age = current_age + year
        
        if year <= years_until_retirement:
            # Calculate accumulation
            for _ in range(min(5, year)):  # Calculate 5-year chunks
                portfolio_value *= (1 + expected_return)
                portfolio_value += 10000
            phase = 'accumulation'
            annual_income = 0
        else:
            # Calculate retirement withdrawals
            withdrawal_rate = 0.04  # 4% rule
            annual_income = portfolio_value * withdrawal_rate
            years_in_retirement = min(5, year - years_until_retirement)
            for _ in range(years_in_retirement):
                portfolio_value = portfolio_value * (1 + expected_return) - annual_income
            phase = 'retirement'
        
        if portfolio_value > 0:
            projections.append({
                'year': year,
                'age': age,
                'portfolio_value': round(portfolio_value, 2),
                'annual_income': round(annual_income, 2),
                'phase': phase
            })
    
    return projections


@function_tool
async def update_job_retirement(analysis: str) -> str:
    """
    Store the retirement analysis in the database.
    
    Args:
        analysis: JSON string containing the complete retirement analysis
    
    Returns:
        Success or error message
    """
    global current_job_id, db
    
    if not current_job_id:
        return "Error: No job ID available"
    
    try:
        # Parse the analysis
        analysis_data = json.loads(analysis)
        
        # Add metadata
        retirement_payload = {
            'analysis': analysis_data,
            'generated_at': datetime.utcnow().isoformat(),
            'agent': 'retirement'
        }
        
        # Update the database
        init_database()
        if db:
            rows_updated = db.jobs.update_retirement(current_job_id, retirement_payload)
            
            if rows_updated > 0:
                logger.info(f"Stored retirement analysis for job {current_job_id}")
                return f"Successfully stored retirement analysis for job {current_job_id}"
            else:
                return f"Failed to update job {current_job_id} with retirement analysis"
        else:
            logger.warning("Database not available, skipping update")
            return "Database not available, analysis not stored"
            
    except Exception as e:
        logger.error(f"Error updating retirement analysis: {e}")
        return f"Error storing retirement analysis: {str(e)}"


async def run_retirement_agent(job_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the retirement specialist agent."""
    global current_job_id
    
    # Set global context
    current_job_id = job_id
    
    # Get user data from database (will now use correct region from ARN)
    init_database()
    years_until_retirement = 30  # Default
    target_income = 80000.0  # Default
    current_age = 40  # Default
    
    if db:
        try:
            # Get the job to find the user
            job = db.jobs.find_by_id(job_id)
            if job and job.get('clerk_user_id'):
                # Get user preferences
                user = db.users.find_by_clerk_id(job['clerk_user_id'])
                if user:
                    years_until_retirement = user.get('years_until_retirement', 30)
                    target_income = float(user.get('target_retirement_income', 80000))
                    # Calculate current age if birth year is available
                    # For now, keep default of 40
        except Exception as e:
            logger.warning(f"Could not load user data: {e}. Using defaults.")
    else:
        logger.warning("Database not available, using default user preferences")
    
    # Calculate portfolio metrics
    portfolio_value = calculate_portfolio_value(portfolio_data)
    allocation = calculate_asset_allocation(portfolio_data)
    
    # Run Monte Carlo simulation in the background
    monte_carlo = run_monte_carlo_simulation(
        portfolio_value,
        years_until_retirement,
        target_income,
        allocation,
        num_simulations=500
    )
    
    # Generate projections
    projections = generate_projections(
        portfolio_value,
        years_until_retirement,
        allocation,
        current_age
    )
    
    # Format comprehensive context for the agent
    analysis_context = f"""
# Portfolio Analysis Context

## Current Situation
- Portfolio Value: ${portfolio_value:,.0f}
- Asset Allocation: {', '.join([f'{k.title()}: {v:.0%}' for k, v in allocation.items() if v > 0])}
- Years to Retirement: {years_until_retirement}
- Target Annual Income: ${target_income:,.0f}
- Current Age: {current_age}

## Monte Carlo Simulation Results (500 scenarios)
- Success Rate: {monte_carlo['success_rate']}% (probability of sustaining retirement income for 30 years)
- Expected Portfolio Value at Retirement: ${monte_carlo['expected_value_at_retirement']:,.0f}
- 10th Percentile Outcome: ${monte_carlo['percentile_10']:,.0f} (worst case)
- Median Final Value: ${monte_carlo['median_final_value']:,.0f}
- 90th Percentile Outcome: ${monte_carlo['percentile_90']:,.0f} (best case)
- Average Years Portfolio Lasts: {monte_carlo['average_years_lasted']} years

## Key Projections (Milestones)
"""
    
    for proj in projections[:6]:  # Show first 6 milestones
        if proj['phase'] == 'accumulation':
            analysis_context += f"- Age {proj['age']}: ${proj['portfolio_value']:,.0f} (building wealth)\n"
        else:
            analysis_context += f"- Age {proj['age']}: ${proj['portfolio_value']:,.0f} (annual income: ${proj['annual_income']:,.0f})\n"
    
    analysis_context += f"""

## Risk Factors to Consider
- Sequence of returns risk (poor returns early in retirement)
- Inflation impact (3% assumed)
- Healthcare costs in retirement
- Longevity risk (living beyond 30 years)
- Market volatility (equity standard deviation: 18%)

## Safe Withdrawal Rate Analysis
- 4% Rule: ${portfolio_value * 0.04:,.0f} initial annual income
- Target Income: ${target_income:,.0f}
- Gap: ${target_income - (portfolio_value * 0.04):,.0f}

Your task: Analyze this retirement readiness data and provide:
1. Clear assessment of retirement readiness
2. Specific recommendations to improve success rate
3. Risk mitigation strategies
4. Action items with timeline

After your analysis, use the update_job_retirement tool to store your complete findings.
"""
    
    # Set region for Bedrock if specified (but remember original)
    if BEDROCK_MODEL_REGION != os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = BEDROCK_MODEL_REGION
        os.environ['AWS_DEFAULT_REGION'] = BEDROCK_MODEL_REGION
    
    # Initialize model
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Create tools (just the storage tool now)
    tools = [update_job_retirement]
    
    # Run the agent
    with trace("Retirement Planning Analysis"):
        agent = Agent(
            name="Retirement Specialist",
            instructions=RETIREMENT_INSTRUCTIONS,
            model=model,
            tools=tools
        )
        
        result = await Runner.run(
            agent,
            input=analysis_context,
            max_turns=5  # Reduced since we're just analyzing and storing
        )
        
        return {
            'success': True,
            'message': 'Retirement analysis completed',
            'final_output': result.final_output
        }


def lambda_handler(event, context):
    """
    Lambda handler for retirement analysis.
    
    Expected event structure:
    {
        "job_id": "uuid",
        "portfolio_data": {...}  # Optional, will load from DB if not provided
    }
    """
    try:
        logger.info("Retirement Specialist Lambda invoked")
        
        # Parse the event
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
            # Try to load from database
            init_database()
            if db:
                job = db.jobs.find_by_id(job_id)
                if job:
                    portfolio_data = job.get('request_payload', {}).get('portfolio_data', {})
                else:
                    return {
                        'statusCode': 404,
                        'body': json.dumps({'error': f'Job {job_id} not found'})
                    }
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No portfolio data provided'})
                }
        
        # Run the retirement analysis (user data will be loaded from DB)
        result = asyncio.run(run_retirement_agent(job_id, portfolio_data))
        
        logger.info(f"Retirement analysis completed for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in retirement analysis: {e}", exc_info=True)
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
        "job_id": "test-retirement-123",
        "portfolio_data": {
            "accounts": [
                {
                    "name": "401(k)",
                    "type": "retirement",
                    "cash_balance": 10000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "current_price": 450,
                                "allocation_asset_class": {"equity": 100}
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 100,
                            "instrument": {
                                "name": "Vanguard Total Bond Market ETF",
                                "current_price": 75,
                                "allocation_asset_class": {"fixed_income": 100}
                            }
                        }
                    ]
                }
            ]
        }
        # Note: user data will be loaded from database based on job_id
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))