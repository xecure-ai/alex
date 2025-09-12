#!/usr/bin/env python3
"""
Test Charter agent locally with LARGE data (same as test_full.py)
This tests if the issue is with the data size or the Lambda environment
"""

import json
import time
import logging
import sys
from dotenv import load_dotenv

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler

load_dotenv(override=True)

# Set up comprehensive logging to capture ALL output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def test_charter_local_large():
    """Test the Charter agent locally with large portfolio data"""
    
    db = Database()
    
    # Create test job
    test_user_id = "test_user_001"
    
    job_create = JobCreate(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={"analysis_type": "test", "test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    
    # Load portfolio data for the test (same as test_full.py)
    user = db.users.find_by_clerk_id(test_user_id)
    accounts = db.accounts.find_by_user(test_user_id)
    
    portfolio_data = {
        'user_id': test_user_id,
        'job_id': job_id,
        'years_until_retirement': user.get('years_until_retirement', 30),
        'accounts': []
    }
    
    for account in accounts:
        positions = db.positions.find_by_account(account['id'])
        account_data = {
            'id': account['id'],
            'name': account['account_name'],
            'cash_balance': float(account.get('cash_balance', 0)),
            'positions': []
        }
        
        for position in positions:
            instrument = db.instruments.find_by_symbol(position['symbol'])
            if instrument:
                account_data['positions'].append({
                    'symbol': position['symbol'],
                    'quantity': float(position['quantity']),
                    'instrument': instrument
                })
        
        portfolio_data['accounts'].append(account_data)
    
    print(f"Testing Charter Agent LOCALLY with LARGE data")
    print(f"Job ID: {job_id}")
    print(f"Number of accounts: {len(portfolio_data['accounts'])}")
    total_positions = sum(len(acc['positions']) for acc in portfolio_data['accounts'])
    print(f"Total positions: {total_positions}")
    print("=" * 60)
    
    # Call lambda_handler directly (not via Lambda)
    event = {
        'job_id': job_id,
        'portfolio_data': portfolio_data
    }
    
    try:
        print("About to call lambda_handler locally...")
        result = lambda_handler(event, {})
        print(f"lambda_handler returned")
        print(f"Status Code: {result.get('statusCode')}")
        
        body = json.loads(result.get('body', '{}'))
        print(f"Success: {body.get('success')}")
        print(f"Message: {body.get('message')}")
        print(f"Charts generated: {body.get('charts_generated', 0)}")
        print(f"Chart keys: {body.get('chart_keys', [])}")
        
        # Check database for results
        time.sleep(2)  # Give it a moment
        job = db.jobs.find_by_id(job_id)
        
        if job and job.get('charts_payload'):
            print(f"\n📊 Charts Created ({len(job['charts_payload'])} total):")
            print("=" * 50)
            for chart_key, chart_data in job['charts_payload'].items():
                print(f"\n🎯 Chart: {chart_key}")
                print(f"   Title: {chart_data.get('title', 'N/A')}")
                print(f"   Type: {chart_data.get('type', 'N/A')}")
                print(f"   Description: {chart_data.get('description', 'N/A')}")
                
                data_points = chart_data.get('data', [])
                print(f"   Data Points ({len(data_points)}):")
                for i, point in enumerate(data_points[:3]):  # Show first 3 for brevity
                    name = point.get('name', 'N/A')
                    value = point.get('value', 0)
                    percentage = point.get('percentage', 0)
                    color = point.get('color', 'N/A')
                    print(f"     {i+1}. {name}: ${value:,.2f} ({percentage:.1f}%) {color}")
                if len(data_points) > 3:
                    print(f"     ... and {len(data_points) - 3} more")
                
                # Verify percentages sum to ~100%
                total_pct = sum(p.get('percentage', 0) for p in data_points)
                print(f"   ✅ Total percentage: {total_pct:.1f}%")
        else:
            print("\n❌ No charts found in database")
            
    except Exception as e:
        print(f"Error calling lambda_handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up test job
        print(f"\nDeleting test job: {job_id}")
        db.jobs.delete(job_id)
    
    print("=" * 60)

if __name__ == "__main__":
    test_charter_local_large()