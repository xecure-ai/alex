#!/usr/bin/env python3
"""
Simple test for Reporter agent
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler

def test_reporter():
    """Test the reporter agent with simple portfolio data"""
    
    # Create a real job in the database
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    print(f"Created test job: {job_id}")
    
    test_event = {
        "job_id": job_id,
        "portfolio_data": {
            "accounts": [
                {
                    "name": "401(k)",
                    "cash_balance": 5000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "current_price": 450,
                                "asset_class": "equity"
                            }
                        }
                    ]
                }
            ]
        },
        "user_data": {
            "years_until_retirement": 25,
            "target_retirement_income": 75000
        }
    }
    
    print("Testing Reporter Agent...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        print(f"Message: {body.get('message', 'N/A')}")
    else:
        print(f"Error: {result['body']}")
    
    # Clean up - delete the test job
    db.jobs.delete(job_id)
    print(f"Deleted test job: {job_id}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_reporter()