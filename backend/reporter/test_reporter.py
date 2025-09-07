"""
Test the Reporter agent locally.
"""

import asyncio
import json
import os
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv(override=True)

# Mock the database update for testing
class MockDB:
    def __init__(self):
        self.stored_reports = {}
    
    async def update_job(self, job_id, update):
        self.stored_reports[job_id] = update.report_payload
        print(f"\n✅ Mock DB: Stored report for job {job_id}")
        return True

# Override the update_job_report function
import agent
original_update = agent.update_job_report

async def mock_update_job_report(job_id: str, report_content: str) -> str:
    """Mock storing the report for testing."""
    print(f"\n📝 Generated Report (length: {len(report_content)} chars):")
    print("-" * 50)
    print(report_content[:1000] + "..." if len(report_content) > 1000 else report_content)
    print("-" * 50)
    return f"Successfully stored report for job {job_id} (mocked)"

agent.update_job_report = mock_update_job_report

async def test_reporter():
    """Test the reporter agent with sample data."""
    
    from lambda_handler import run_reporter_agent
    
    job_id = f"test-{uuid4()}"
    
    portfolio_data = {
        "accounts": [
            {
                "id": "acc1",
                "name": "401(k) Account",
                "type": "401k",
                "cash_balance": 10000.00,
                "positions": [
                    {
                        "symbol": "VTI",
                        "quantity": 150,
                        "instrument": {
                            "name": "Vanguard Total Stock Market ETF",
                            "type": "etf",
                            "asset_class": "equity",
                            "current_price": 230.50,
                            "regions": [
                                {"name": "north_america", "percentage": 100}
                            ],
                            "sectors": [
                                {"name": "technology", "percentage": 30},
                                {"name": "healthcare", "percentage": 15},
                                {"name": "financials", "percentage": 13}
                            ]
                        }
                    },
                    {
                        "symbol": "BND",
                        "quantity": 100,
                        "instrument": {
                            "name": "Vanguard Total Bond Market ETF",
                            "type": "etf",
                            "asset_class": "fixed_income",
                            "current_price": 75.20,
                            "regions": [
                                {"name": "north_america", "percentage": 95},
                                {"name": "international", "percentage": 5}
                            ]
                        }
                    }
                ]
            },
            {
                "id": "acc2",
                "name": "IRA",
                "type": "ira",
                "cash_balance": 5000.00,
                "positions": [
                    {
                        "symbol": "QQQ",
                        "quantity": 50,
                        "instrument": {
                            "name": "Invesco QQQ Trust",
                            "type": "etf",
                            "asset_class": "equity",
                            "current_price": 380.00,
                            "regions": [
                                {"name": "north_america", "percentage": 100}
                            ],
                            "sectors": [
                                {"name": "technology", "percentage": 50},
                                {"name": "communications", "percentage": 20}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    user_data = {
        "years_until_retirement": 20,
        "target_retirement_income": 80000
    }
    
    print(f"🚀 Testing Reporter Agent")
    print(f"   Job ID: {job_id}")
    print(f"   Portfolio: {len(portfolio_data['accounts'])} accounts, multiple positions")
    print(f"   User: {user_data['years_until_retirement']} years to retirement")
    
    try:
        result = await run_reporter_agent(job_id, portfolio_data, user_data)
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Result: {result.get('message')}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reporter())