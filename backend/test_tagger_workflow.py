#!/usr/bin/env python3
"""
Test the tagger workflow with unknown instruments.
This verifies that the planner automatically invokes the tagger
when it encounters instruments not in the database.
"""

import json
import time
import uuid
import boto3
from decimal import Decimal

from src import Database

def test_tagger_workflow():
    """Test that unknown instruments trigger the tagger agent"""
    
    # Initialize database
    db = Database()
    
    # First, ensure NEWETF exists but without allocations (simulating unknown instrument)
    unknown = db.instruments.find_by_symbol('NEWETF')
    if not unknown:
        # Create it directly without allocations using raw SQL
        sql = """INSERT INTO instruments (symbol, name, instrument_type, current_price, 
                 allocation_regions, allocation_sectors, allocation_asset_class) 
                 VALUES (:symbol, :name, :type, :price, :regions, :sectors, :asset_class)"""
        params = [
            {'name': 'symbol', 'value': {'stringValue': 'NEWETF'}},
            {'name': 'name', 'value': {'stringValue': 'New Test ETF'}},
            {'name': 'type', 'value': {'stringValue': 'etf'}},
            {'name': 'price', 'value': {'stringValue': '100.00'}},
            {'name': 'regions', 'value': {'stringValue': '{}'}},
            {'name': 'sectors', 'value': {'stringValue': '{}'}},
            {'name': 'asset_class', 'value': {'stringValue': '{}'}}
        ]
        db.client.execute(sql, params)
        print('Created NEWETF without allocations (simulating unknown instrument)')
    else:
        # Clear allocations if they exist
        sql = """UPDATE instruments SET allocation_regions = '{}', allocation_sectors = '{}', 
                 allocation_asset_class = '{}' WHERE symbol = :symbol"""
        params = [{'name': 'symbol', 'value': {'stringValue': 'NEWETF'}}]
        db.client.execute(sql, params)
        print('Cleared NEWETF allocations')
    
    # Verify NEWETF exists but has no allocations
    unknown = db.instruments.find_by_symbol('NEWETF')
    print(f'NEWETF before test:')
    print(f'  Price: ${unknown.get("current_price")}')
    regions = unknown.get("allocation_regions", {})
    sectors = unknown.get("allocation_sectors", {})
    asset_class = unknown.get("allocation_asset_class", {})
    has_allocations = any([regions, sectors, asset_class])
    print(f'  Allocations: {"Found" if has_allocations else "Empty (will trigger tagger)"}')
    
    # Create a test user
    test_user_id = f'test_tagger_{uuid.uuid4().hex[:8]}'
    user_id = db.users.create_user(
        clerk_user_id=test_user_id,
        display_name='Tagger Test',
        years_until_retirement=25,
        target_retirement_income=Decimal('100000')
    )
    print(f'\nCreated test user: {test_user_id}')
    
    # Create account
    account_id = db.accounts.create_account(
        clerk_user_id=test_user_id,
        account_name='Test Account',
        account_purpose='taxable_brokerage',
        cash_balance=Decimal('1000.0')
    )
    print(f'Created account: {account_id}')
    
    # Add positions including the instrument with empty allocations
    positions = [
        ('SPY', 100),
        ('NEWETF', 50),  # Instrument with empty allocations
        ('BND', 200)
    ]
    
    for symbol, quantity in positions:
        sql = "INSERT INTO positions (account_id, symbol, quantity) VALUES (:account_id::uuid, :symbol, :quantity)"
        params = [
            {'name': 'account_id', 'value': {'stringValue': account_id}},
            {'name': 'symbol', 'value': {'stringValue': symbol}},
            {'name': 'quantity', 'value': {'longValue': quantity}}
        ]
        db.client.execute(sql, params)
    
    print(f'Added positions including unknown instrument NEWETF')
    
    # Create a job
    job = db.jobs.create(test_user_id)
    print(f'Created job: {job.job_id}')
    
    print(f'\nTest data ready:')
    print(f'  Job ID: {job.job_id}')
    print(f'  User ID: {test_user_id}')
    
    # Now trigger the planner via SQS
    sqs = boto3.client('sqs', region_name='us-east-1')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/392340646348/alex-analysis-jobs'
    
    message = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'job_id': job.job_id})
    )
    print(f'\nSent message to SQS: {message["MessageId"]}')
    print('Monitoring job progress...')
    
    # Monitor job
    for i in range(60):  # Max 2 minutes
        time.sleep(2)
        job_status = db.jobs.get(job.job_id)
        status = job_status.get('status', 'unknown')
        print(f'  [{i*2:3}s] Status: {status}')
        if status in ['completed', 'failed']:
            break
    
    # Check if NEWETF allocations were populated by tagger
    unknown_after = db.instruments.find_by_symbol('NEWETF')
    print(f'\n=== TAGGER WORKFLOW VERIFICATION ===')
    if unknown_after:
        print(f'NEWETF after processing:')
        print(f'  Price: ${unknown_after.get("current_price")}')
        regions = unknown_after.get("allocation_regions", {})
        sectors = unknown_after.get("allocation_sectors", {})
        asset_class = unknown_after.get("allocation_asset_class", {})
        has_allocations_after = any([regions, sectors, asset_class])
        
        if has_allocations_after:
            print(f'  ✅ Allocations populated by tagger: YES')
            print(f'    Regions: {regions}')
            print(f'    Sectors: {sectors}')
            print(f'    Asset Class: {asset_class}')
            success = True
        else:
            print(f'  ❌ Allocations NOT populated - tagger may not have been called')
            success = False
    else:
        print('  ❌ NEWETF not found in database')
        success = False
    
    # Check job results
    print(f'\n=== JOB RESULTS ===')
    if job_status.get('summary_payload'):
        summary = job_status['summary_payload']
        print(f'Summary: {summary.get("summary", "N/A")[:200]}...')
    
    # Clean up
    print(f'\nCleaning up test data...')
    try:
        # Delete job
        sql = "DELETE FROM jobs WHERE job_id = :job_id"
        params = [{'name': 'job_id', 'value': {'stringValue': job.job_id}}]
        db.client.execute(sql, params)
        
        # Delete positions and accounts
        sql = "DELETE FROM positions WHERE account_id IN (SELECT account_id FROM accounts WHERE clerk_user_id = :user_id)"
        params = [{'name': 'user_id', 'value': {'stringValue': test_user_id}}]
        db.client.execute(sql, params)
        
        sql = "DELETE FROM accounts WHERE clerk_user_id = :user_id"
        params = [{'name': 'user_id', 'value': {'stringValue': test_user_id}}]
        db.client.execute(sql, params)
        
        # Delete user
        sql = "DELETE FROM users WHERE clerk_user_id = :user_id"
        params = [{'name': 'user_id', 'value': {'stringValue': test_user_id}}]
        db.client.execute(sql, params)
        
        print('Test data cleaned up successfully')
    except Exception as e:
        print(f'Warning: Cleanup failed: {e}')
    
    print('\n✅ Tagger workflow test complete!')
    
    # Return success/failure
    return success

if __name__ == '__main__':
    success = test_tagger_workflow()
    exit(0 if success else 1)