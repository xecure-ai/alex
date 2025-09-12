#!/usr/bin/env python
"""
Test Charter Lambda with SIMPLE data (matching test_simple.py) but via remote invocation.
This tests whether the data complexity is causing the issue.
"""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database
from src.schemas import JobCreate

def test_charter_with_simple_data():
    """Test Charter Lambda with the same simple data as test_simple.py"""
    
    db = Database()
    lambda_client = boto3.client('lambda')
    
    # Create a job for tracking
    job_create = JobCreate(
        clerk_user_id="test_user_001",  # Use existing test user
        job_type="portfolio_analysis",
        request_payload={"test": "simple_remote"}
    )
    job_id = db.jobs.create(job_create.model_dump())
    
    # Use the EXACT same simple portfolio as test_simple.py
    simple_portfolio_data = {
        "user_id": "test_simple_remote",
        "job_id": job_id,
        "years_until_retirement": 25,
        "accounts": [
            {
                "id": "simple_account_001",
                "name": "401(k)",
                "type": "401k", 
                "cash_balance": 5000,
                "positions": [
                    {
                        "symbol": "SPY",
                        "quantity": 100,
                        "instrument": {
                            "symbol": "SPY",
                            "name": "SPDR S&P 500 ETF",
                            "instrument_type": "etf",
                            "current_price": 450,
                            "allocation_asset_class": {"equity": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {
                                "technology": 30,
                                "healthcare": 15,
                                "financials": 15,
                                "consumer_discretionary": 20,
                                "industrials": 20
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    print(f"Testing Charter Lambda with SIMPLE data")
    print(f"Job ID: {job_id}")
    print("=" * 60)
    
    # Invoke Lambda with simple data
    try:
        response = lambda_client.invoke(
            FunctionName='alex-charter',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'job_id': job_id,
                'portfolio_data': simple_portfolio_data
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda Response: {json.dumps(result, indent=2)}")
        
        # Check database for results
        import time
        time.sleep(2)
        job = db.jobs.find_by_id(job_id)
        
        if job and job.get('charts_payload'):
            print(f"\n✅ SUCCESS! Charts Created: {len(job['charts_payload'])} charts")
            print(f"Chart keys: {list(job['charts_payload'].keys())}")
        else:
            print("\n❌ FAILURE! No charts found in database")
            
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    finally:
        # Clean up
        db.jobs.delete(job_id)
        print(f"\nDeleted test job: {job_id}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_charter_with_simple_data()