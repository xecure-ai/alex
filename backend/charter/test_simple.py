#!/usr/bin/env python3
"""
Simple test for Charter agent
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler

def test_charter():
    """Test the charter agent with simple portfolio data"""
    
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
                                "allocation_sectors": {"technology": 30, "healthcare": 15, "financials": 15}
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    print("Testing Charter Agent...")
    print("=" * 60)
    
    import sys
    print("About to call lambda_handler...", flush=True)
    sys.stdout.flush()
    result = lambda_handler(test_event, None)
    print("lambda_handler returned", flush=True)
    
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
    test_charter()