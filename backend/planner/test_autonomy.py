#!/usr/bin/env python3
"""
Test agent autonomy with different portfolio scenarios
Phase 6.3 and 6.4 - Full End-to-End and Autonomy Tests
"""

import os
import json
import boto3
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database

db = Database()
sqs = boto3.client('sqs')

# Get queue URL
QUEUE_NAME = 'alex-analysis-jobs'
response = sqs.list_queues(QueueNamePrefix=QUEUE_NAME)
queue_url = None
for url in response.get('QueueUrls', []):
    if QUEUE_NAME in url:
        queue_url = url
        break

def run_job(user_id, test_name):
    """Create and monitor a job"""
    print(f"\n🚀 Running test: {test_name}")
    print("-" * 50)
    
    # Create job
    job_data = {
        'clerk_user_id': user_id,
        'job_type': 'portfolio_analysis',
        'status': 'pending',
        'request_payload': {
            'analysis_type': 'full',
            'test_name': test_name,
            'requested_at': datetime.now(timezone.utc).isoformat()
        }
    }
    
    job_id = db.jobs.create(job_data)
    print(f"Created job: {job_id}")
    
    # Send to SQS
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'job_id': job_id})
    )
    print(f"Message sent: {response['MessageId']}")
    
    # Monitor job
    print("Monitoring job progress...")
    start_time = time.time()
    timeout = 180  # 3 minutes
    last_status = None
    
    while time.time() - start_time < timeout:
        job = db.jobs.find_by_id(job_id)
        status = job['status']
        
        if status != last_status:
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed:3d}s] Status: {status}")
            last_status = status
        
        if status == 'completed':
            # Check results
            charts_count = len(job.get('charts_payload', {}))
            has_report = bool(job.get('report_payload'))
            has_retirement = bool(job.get('retirement_payload'))
            
            print(f"✅ Completed!")
            print(f"   Charts: {charts_count}")
            print(f"   Report: {'Yes' if has_report else 'No'}")
            print(f"   Retirement: {'Yes' if has_retirement else 'No'}")
            
            # Check which agents were likely called
            if charts_count > 0:
                print("   → Charter agent was called")
            if has_report:
                print("   → Reporter agent was called")
            if has_retirement:
                print("   → Retirement agent was called")
                
            return True
            
        elif status == 'failed':
            print(f"❌ Failed: {job.get('error_message', 'Unknown error')}")
            return False
        
        time.sleep(2)
    
    print("❌ Timed out")
    return False


def test_simple_portfolio():
    """Test with a simple portfolio (1 position) - should skip some agents"""
    print("\n" + "=" * 70)
    print("📊 TEST 1: Simple Portfolio (1 position)")
    print("Expected: Planner might skip charter for such a simple portfolio")
    print("=" * 70)
    
    # Create a test user with simple portfolio
    user_id = 'test_simple_001'
    
    # Check if user exists, if not create
    user = db.users.find_by_clerk_id(user_id)
    if not user:
        db.users.create_user(clerk_user_id=user_id, display_name='Simple Test User')
        
        # Create single account with one position
        account_id = db.accounts.create_account(
            clerk_user_id=user_id,
            account_name='Simple 401k',
            account_purpose='401k',
            cash_balance=1000.0
        )
        
        # Add single position
        db.positions.add_position(
            account_id=account_id,
            symbol='SPY',
            quantity=10.0
        )
        print(f"Created simple portfolio for {user_id}")
    
    return run_job(user_id, "Simple Portfolio Test")


def test_complex_portfolio():
    """Test with the existing complex portfolio (11 positions)"""
    print("\n" + "=" * 70)
    print("📊 TEST 2: Complex Portfolio (11+ positions)")
    print("Expected: Planner should call all agents including charter")
    print("=" * 70)
    
    # Use existing test user with full portfolio
    return run_job('test_user_001', "Complex Portfolio Test")


def test_no_retirement_goals():
    """Test with user having no retirement goals set"""
    print("\n" + "=" * 70)
    print("📊 TEST 3: No Retirement Goals")
    print("Expected: Planner might skip retirement agent")
    print("=" * 70)
    
    # Create user with no retirement goals
    user_id = 'test_no_retire_001'
    
    user = db.users.find_by_clerk_id(user_id)
    if not user:
        db.users.create_user(
            clerk_user_id=user_id,
            display_name='No Retirement User',
            years_until_retirement=None,  # No retirement goals
            target_retirement_income=None
        )
        
        # Create account with some positions
        account_id = db.accounts.create_account(
            clerk_user_id=user_id,
            account_name='Taxable Account',
            account_purpose='taxable',
            cash_balance=5000.0
        )
        
        # Add a few positions
        for symbol, qty in [('QQQ', 20), ('BND', 30)]:
            db.positions.add_position(
                account_id=account_id,
                symbol=symbol,
                quantity=qty
            )
        print(f"Created portfolio without retirement goals for {user_id}")
    
    return run_job(user_id, "No Retirement Goals Test")


def main():
    print("=" * 70)
    print("🎯 Agent Autonomy Test Suite")
    print("Testing Planner's decision-making with different portfolios")
    print("=" * 70)
    
    if not queue_url:
        print("❌ Queue not found")
        return 1
    
    results = []
    
    # Run tests
    results.append(("Simple Portfolio", test_simple_portfolio()))
    time.sleep(5)  # Brief pause between tests
    
    results.append(("Complex Portfolio", test_complex_portfolio()))
    time.sleep(5)
    
    results.append(("No Retirement Goals", test_no_retirement_goals()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("=" * 70)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All autonomy tests passed!")
    else:
        print("\n⚠️ Some tests failed - check logs for details")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())