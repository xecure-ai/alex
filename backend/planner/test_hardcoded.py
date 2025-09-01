#!/usr/bin/env python3
"""
Test orchestrator with hard-coded tool returns and structured output
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lambda_handler import run_orchestrator, PortfolioData, UserPreferences, AccountInfo, PositionInfo, InstrumentInfo
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_orchestrator():
    """Test the orchestrator with hard-coded tool returns"""
    
    logger.info("="*60)
    logger.info("Testing Orchestrator with Hard-coded Tools")
    logger.info("="*60)
    
    # Create test portfolio data WITH POSITIONS
    portfolio_data = PortfolioData(
        user_id="test_user_001",
        job_id="test_job_001",
        user_preferences=UserPreferences(
            years_until_retirement=30,
            target_retirement_income=80000.0
        ),
        accounts=[
            AccountInfo(
                id="acc1",
                name="401k",
                cash_balance=10000.0,
                positions=[
                    PositionInfo(
                        symbol="SPY",
                        quantity=100.0,
                        instrument=InstrumentInfo(
                            symbol="SPY",
                            name="SPDR S&P 500 ETF",
                            has_allocations=True
                        )
                    ),
                    PositionInfo(
                        symbol="AGG",
                        quantity=50.0,
                        instrument=InstrumentInfo(
                            symbol="AGG",
                            name="iShares Core US Aggregate Bond ETF",
                            has_allocations=True
                        )
                    )
                ]
            ),
            AccountInfo(
                id="acc2",
                name="Brokerage",
                cash_balance=5000.0,
                positions=[
                    PositionInfo(
                        symbol="AAPL",
                        quantity=10.0,
                        instrument=InstrumentInfo(
                            symbol="AAPL",
                            name="Apple Inc",
                            has_allocations=True
                        )
                    )
                ]
            )
        ]
    )
    
    logger.info("Portfolio data being sent:")
    logger.info(f"- User: {portfolio_data.user_id}")
    logger.info(f"- Accounts: {len(portfolio_data.accounts)}")
    total_positions = sum(len(acc.positions) for acc in portfolio_data.accounts)
    logger.info(f"- Total positions: {total_positions}")
    for acc in portfolio_data.accounts:
        logger.info(f"  - {acc.name}: {len(acc.positions)} positions, ${acc.cash_balance:.2f} cash")
    
    logger.info("-"*40)
    
    try:
        # Run the orchestrator
        result = await run_orchestrator(portfolio_data)
        
        logger.info("-"*40)
        logger.info("Orchestrator completed!")
        logger.info(f"Status: {result.status}")
        logger.info(f"Summary length: {len(result.summary) if result.summary else 0} chars")
        logger.info(f"Key findings: {len(result.key_findings)} items")
        logger.info(f"Recommendations: {len(result.recommendations)} items")
        
        if result.error_message:
            logger.info(f"Error message: {result.error_message}")
        
        if result.status == "completed":
            logger.info("\n✅ SUCCESS: Analysis completed!")
            logger.info("\nSummary preview:")
            logger.info(result.summary[:200] + "..." if len(result.summary) > 200 else result.summary)
        else:
            logger.error(f"\n❌ FAILED: {result.error_message}")
            
    except Exception as e:
        logger.error(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())