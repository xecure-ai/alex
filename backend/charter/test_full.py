#!/usr/bin/env python3
"""
Full test for Charter agent via Lambda
"""

import os
import json
import boto3
import time
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database
from src.schemas import JobCreate

def test_charter_lambda():
    """Test the Charter agent via Lambda invocation"""
    
    db = Database()
    lambda_client = boto3.client('lambda')
    
    # Create test job
    test_user_id = "test_user_001"
    
    job_create = JobCreate(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={"analysis_type": "test", "test": True}
    )
    job = db.jobs.create(job_create.model_dump())
    job_id = job['id']
    
    # Load portfolio data for the test
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
    
    print(f"Testing Charter Lambda with job {job_id}")
    print("=" * 60)
    
    # Invoke Lambda
    try:
        response = lambda_client.invoke(
            FunctionName='alex-charter',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'job_id': job_id,
                'portfolio_data': portfolio_data
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda Response: {json.dumps(result, indent=2)}")
        
        # Check database for results
        time.sleep(2)  # Give it a moment
        job = db.jobs.find_by_id(job_id)
        
        if job and job.get('charts_payload'):
            print("\n✅ Charts generated successfully!")
            print(f"Number of charts: {len(job['charts_payload'])}")
            for chart_key in list(job['charts_payload'].keys())[:3]:
                print(f"  - {chart_key}")
        else:
            print("\n❌ No charts found in database")
            
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_charter_lambda()