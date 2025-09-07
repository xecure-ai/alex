"""
Retirement Specialist Agent Lambda Handler
Provides retirement planning analysis and projections.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import random
import math

from pydantic import BaseModel, Field
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
# Try to load .env file if available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # dotenv not available in Lambda, use environment variables

from templates import RETIREMENT_INSTRUCTIONS, RETIREMENT_ANALYSIS_TEMPLATE


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_MODEL_REGION = os.getenv('BEDROCK_MODEL_REGION', os.getenv('AWS_REGION', 'us-east-1'))

class ProjectionDataPoint(BaseModel):
    """Data point for retirement projections"""
    year: int = Field(description="Year of projection")
    age: int = Field(description="Age at this year")
    portfolio_value: float = Field(description="Projected portfolio value")
    annual_income: float = Field(description="Projected annual income")
    inflation_adjusted_income: float = Field(description="Income adjusted for inflation")

class MonteCarloResult(BaseModel):
    """Monte Carlo simulation results"""
    success_rate: float = Field(description="Percentage of successful scenarios")
    median_final_value: float = Field(description="Median portfolio value at end")
    percentile_10: float = Field(description="10th percentile outcome")
    percentile_90: float = Field(description="90th percentile outcome")
    years_of_income: float = Field(description="Average years of target income coverage")

class RetirementAnalysis(BaseModel):
    """Complete retirement analysis results"""
    current_trajectory_value: float = Field(description="Expected portfolio value at retirement")
    projected_annual_income: float = Field(description="Expected annual retirement income")
    income_gap: float = Field(description="Gap between projected and target income")
    success_probability: float = Field(description="Probability of meeting retirement goals")
    monte_carlo_results: MonteCarloResult = Field(description="Monte Carlo simulation results")
    projections: List[ProjectionDataPoint] = Field(description="Year-by-year projections")
    recommendations: List[str] = Field(description="Specific retirement planning recommendations")
    key_risks: List[str] = Field(description="Primary risks to retirement plan")

def estimate_portfolio_value(portfolio_data: Dict[str, Any]) -> float:
    """Estimate current portfolio value (simplified without prices)."""
    # This is a simplified estimation
    # In reality, we'd need current prices
    total_positions = 0
    
    for account in portfolio_data.get('accounts', []):
        cash = account.get('cash_balance', 0)
        total_positions += cash
        
        # Estimate position values (very rough)
        for position in account.get('positions', []):
            symbol = position.get('symbol')
            quantity = position.get('quantity', 0)
            
            # Rough estimates for common ETFs
            estimated_prices = {
                'SPY': 450,
                'QQQ': 390,
                'BND': 75,
                'VTI': 240,
                'IWM': 200,
                'EFA': 75,
                'GLD': 180,
                'TLT': 90
            }
            
            # Use estimated price or default
            price = estimated_prices.get(symbol, 100)
            total_positions += quantity * price
    
    return total_positions

def calculate_asset_allocation(portfolio_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate rough asset allocation percentages."""
    equity_weight = 0.6  # Default 60/40
    bond_weight = 0.4
    
    # Try to get actual allocation from instruments
    total_equity = 0
    total_bonds = 0
    total_positions = 0
    
    for account in portfolio_data.get('accounts', []):
        for position in account.get('positions', []):
            instrument = position.get('instrument', {})
            asset_class = instrument.get('allocation_asset_class', {})
            
            if asset_class:
                equity_pct = asset_class.get('equity', 0) / 100
                bond_pct = asset_class.get('fixed_income', 0) / 100
                
                total_equity += equity_pct
                total_bonds += bond_pct
                total_positions += 1
    
    if total_positions > 0:
        equity_weight = total_equity / total_positions
        bond_weight = total_bonds / total_positions
    
    return {
        'equity': equity_weight,
        'bonds': bond_weight
    }

def run_monte_carlo_simulation(
    current_value: float,
    years_until_retirement: int,
    retirement_years: int,
    target_income: float,
    asset_allocation: Dict[str, float],
    num_simulations: int = 1000
) -> Dict[str, Any]:
    """Run Monte Carlo simulation for retirement outcomes."""
    
    # Market assumptions
    equity_return_mean = 0.07
    equity_return_std = 0.18
    bond_return_mean = 0.04
    bond_return_std = 0.05
    inflation_rate = 0.03
    
    successful_scenarios = 0
    final_values = []
    years_lasted = []
    
    for _ in range(num_simulations):
        portfolio_value = current_value
        
        # Accumulation phase
        for year in range(years_until_retirement):
            equity_return = random.gauss(equity_return_mean, equity_return_std)
            bond_return = random.gauss(bond_return_mean, bond_return_std)
            
            portfolio_return = (
                asset_allocation['equity'] * equity_return +
                asset_allocation['bonds'] * bond_return
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
            
            portfolio_return = (
                asset_allocation['equity'] * equity_return +
                asset_allocation['bonds'] * bond_return
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
    
    return {
        'success_rate': success_rate,
        'median_final_value': final_values[num_simulations // 2],
        'percentile_10': final_values[num_simulations // 10],
        'percentile_90': final_values[9 * num_simulations // 10],
        'average_years_lasted': sum(years_lasted) / len(years_lasted)
    }

def generate_projections(
    current_value: float,
    years_until_retirement: int,
    asset_allocation: Dict[str, float],
    current_age: int = 40
) -> List[Dict[str, Any]]:
    """Generate year-by-year retirement projections."""
    projections = []
    portfolio_value = current_value
    
    # Expected returns
    expected_return = (
        asset_allocation['equity'] * 0.07 +
        asset_allocation['bonds'] * 0.04
    )
    
    # Accumulation phase
    for year in range(years_until_retirement + 30):  # Project 30 years into retirement
        age = current_age + year
        
        if year < years_until_retirement:
            # Still accumulating
            portfolio_value *= (1 + expected_return)
            portfolio_value += 10000  # Annual contribution
            annual_income = 0
            inflation_adjusted_income = 0
        else:
            # In retirement
            withdrawal_rate = 0.04  # 4% rule
            annual_income = portfolio_value * withdrawal_rate
            years_in_retirement = year - years_until_retirement
            inflation_adjusted_income = annual_income / ((1.03) ** years_in_retirement)
            portfolio_value = portfolio_value * (1 + expected_return) - annual_income
        
        projections.append({
            'year': year,
            'age': age,
            'portfolio_value': round(portfolio_value, 2),
            'annual_income': round(annual_income, 2),
            'inflation_adjusted_income': round(inflation_adjusted_income, 2)
        })
    
    return projections

async def analyze_retirement(portfolio_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> RetirementAnalysis:
    """Perform comprehensive retirement analysis using AI."""
    
    # Set region for Bedrock if specified
    if BEDROCK_MODEL_REGION != os.getenv('AWS_REGION', 'us-east-1'):
        os.environ["AWS_REGION_NAME"] = BEDROCK_MODEL_REGION
        os.environ["AWS_REGION"] = BEDROCK_MODEL_REGION
        os.environ["AWS_DEFAULT_REGION"] = BEDROCK_MODEL_REGION
    
    # Initialize the model
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Extract user preferences
    years_until_retirement = user_preferences.get('years_until_retirement', 30)
    target_income = user_preferences.get('target_retirement_income', 80000)
    
    # Estimate current portfolio value
    current_value = estimate_portfolio_value(portfolio_data)
    
    # Calculate asset allocation
    asset_allocation = calculate_asset_allocation(portfolio_data)
    
    # Run Monte Carlo simulation
    monte_carlo = run_monte_carlo_simulation(
        current_value,
        years_until_retirement,
        30,  # 30 years in retirement
        target_income,
        asset_allocation
    )
    
    # Generate projections
    projections = generate_projections(
        current_value,
        years_until_retirement,
        asset_allocation
    )
    
    # Prepare data for AI analysis
    portfolio_summary = f"""
Current Portfolio Value: ${current_value:,.0f}
Asset Allocation: {asset_allocation['equity']:.0%} Equity / {asset_allocation['bonds']:.0%} Bonds
Years to Retirement: {years_until_retirement}
Target Annual Income: ${target_income:,.0f}

Monte Carlo Results:
- Success Rate: {monte_carlo['success_rate']:.1f}%
- Median Final Value: ${monte_carlo['median_final_value']:,.0f}
- 10th Percentile: ${monte_carlo['percentile_10']:,.0f}
- 90th Percentile: ${monte_carlo['percentile_90']:,.0f}
"""
    
    # Create analysis task
    task = RETIREMENT_ANALYSIS_TEMPLATE.format(
        portfolio_data=portfolio_summary,
        years_until_retirement=years_until_retirement,
        target_income=target_income
    )
    
    # Run the retirement specialist agent
    with trace("Retirement Analysis"):
        agent = Agent(
            name="Retirement Specialist",
            instructions=RETIREMENT_INSTRUCTIONS,
            model=model,
            output_type=RetirementAnalysis
        )
        
        result = await Runner.run(
            agent,
            input=task,
            max_turns=5
        )
        
        analysis = result.final_output_as(RetirementAnalysis)
        
        # Override with our calculated values
        analysis.monte_carlo_results = MonteCarloResult(
            success_rate=monte_carlo['success_rate'],
            median_final_value=monte_carlo['median_final_value'],
            percentile_10=monte_carlo['percentile_10'],
            percentile_90=monte_carlo['percentile_90'],
            years_of_income=monte_carlo['average_years_lasted']
        )
        
        # Use our projections
        analysis.projections = [
            ProjectionDataPoint(**proj) for proj in projections[:10]  # First 10 years
        ]
        
        return analysis

def lambda_handler(event, context):
    """
    Lambda handler for retirement analysis.
    
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
        logger.info("Retirement Specialist Lambda invoked")
        
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
        
        # Perform retirement analysis
        analysis = asyncio.run(analyze_retirement(portfolio_data, user_preferences))
        
        # Convert to dictionary format
        analysis_dict = {
            'current_trajectory_value': analysis.current_trajectory_value,
            'projected_annual_income': analysis.projected_annual_income,
            'income_gap': analysis.income_gap,
            'success_probability': analysis.success_probability,
            'monte_carlo_results': analysis.monte_carlo_results.model_dump(),
            'projections': [proj.model_dump() for proj in analysis.projections],
            'recommendations': analysis.recommendations,
            'key_risks': analysis.key_risks
        }
        
        logger.info("Retirement analysis completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'analysis': analysis_dict
            })
        }
        
    except Exception as e:
        logger.error(f"Error in retirement analysis: {e}")
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
                    "cash_balance": 10000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "allocation_asset_class": {"equity": 100}
                            }
                        },
                        {
                            "symbol": "BND",
                            "quantity": 100,
                            "instrument": {
                                "name": "Vanguard Total Bond Market ETF",
                                "allocation_asset_class": {"fixed_income": 100}
                            }
                        }
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