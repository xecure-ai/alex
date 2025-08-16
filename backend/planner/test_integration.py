#!/usr/bin/env python3
"""
Integration test for the complete agent orchestration.
This script submits a test job to SQS and monitors its completion.

Usage:
    cd backend/planner
    uv run test_integration.py
"""

import boto3
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Database

def create_test_job(db: Database, user_id: str) -> str:
    """
    Create a test job in the database.
    
    Args:
        db: Database connection
        user_id: User ID for the job
        
    Returns:
        Job ID
    """
    job = db.jobs.create_job(
        clerk_user_id=user_id,
        job_type="portfolio_analysis",
        request_payload={
            'analysis_type': 'full',
            'include_retirement': True,
            'test_job': True
        }
    )
    return job

def submit_job_to_sqs(job_id: str, queue_url: str) -> bool:
    """
    Submit a job to the SQS queue.
    
    Args:
        job_id: Job ID to process
        queue_url: SQS queue URL
        
    Returns:
        True if successful
    """
    sqs_client = boto3.client('sqs')
    
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'job_id': job_id,
                'timestamp': datetime.now().isoformat()
            })
        )
        print(f"✓ Message sent to SQS: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"✗ Failed to send message: {e}")
        return False

def monitor_job_status(db: Database, job_id: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Monitor job status until completion or timeout.
    
    Args:
        db: Database connection
        job_id: Job ID to monitor
        timeout: Maximum seconds to wait
        
    Returns:
        Final job status
    """
    start_time = time.time()
    last_status = None
    
    print(f"⏳ Monitoring job {job_id}...")
    print("   Status updates:")
    
    while time.time() - start_time < timeout:
        job = db.jobs.find_by_id(job_id)
        
        if not job:
            print(f"   ✗ Job {job_id} not found")
            return None
        
        status = job['status']
        
        # Print status change
        if status != last_status:
            elapsed = int(time.time() - start_time)
            print(f"   [{elapsed:3d}s] {last_status or 'pending'} → {status}")
            last_status = status
        
        # Check if job is complete
        if status in ['completed', 'failed']:
            return job
        
        # Wait before next check
        time.sleep(5)
    
    print(f"   ⏱️  Timeout after {timeout} seconds")
    return job

def display_job_results(job: Dict[str, Any]):
    """Display job results in a formatted way."""
    print()
    print("=" * 60)
    print("📊 Job Results")
    print("=" * 60)
    
    print(f"Job ID: {job['id']}")
    print(f"Status: {job['status']}")
    print(f"Created: {job['created_at']}")
    print(f"Updated: {job['updated_at']}")
    
    if job['status'] == 'completed':
        print()
        print("✅ Analysis completed successfully!")
        
        if job.get('result_payload'):
            result = job['result_payload']
            
            if result.get('summary'):
                print()
                print("📝 Summary:")
                print(f"   {result['summary']}")
            
            if result.get('key_findings'):
                print()
                print("🔍 Key Findings:")
                for finding in result['key_findings']:
                    print(f"   • {finding}")
            
            if result.get('recommendations'):
                print()
                print("💡 Recommendations:")
                for rec in result['recommendations']:
                    print(f"   • {rec}")
    
    elif job['status'] == 'failed':
        print()
        print("❌ Job failed!")
        if job.get('error_message'):
            print(f"Error: {job['error_message']}")

def main():
    """Run the integration test."""
    print("🧪 Alex Agent Orchestration Integration Test")
    print("=" * 60)
    
    # Get AWS info
    try:
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.Session().region_name
        print(f"AWS Account: {account_id}")
        print(f"AWS Region: {region}")
    except Exception as e:
        print(f"❌ Failed to get AWS account info: {e}")
        sys.exit(1)
    
    # Get SQS queue URL
    queue_name = 'alex-analysis-jobs'
    queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"
    print(f"SQS Queue: {queue_name}")
    
    # Initialize database
    print()
    print("🔌 Connecting to database...")
    db = Database()
    
    # Check for test user
    test_user_id = 'test_user_001'
    user = db.users.find_by_clerk_id(test_user_id)
    
    if not user:
        print(f"❌ Test user '{test_user_id}' not found")
        print("   Run: cd ../database && uv run reset_db.py --with-test-data")
        sys.exit(1)
    
    print(f"✓ Found test user: {user.get('display_name', test_user_id)}")
    
    # Check user has portfolio data
    accounts = db.accounts.find_by_user(test_user_id)
    if not accounts:
        print("❌ Test user has no accounts")
        print("   Run: cd ../database && uv run reset_db.py --with-test-data")
        sys.exit(1)
    
    total_positions = 0
    for account in accounts:
        positions = db.positions.find_by_account(account['id'])
        total_positions += len(positions)
    
    print(f"✓ Portfolio: {len(accounts)} accounts, {total_positions} positions")
    
    # Create test job
    print()
    print("📝 Creating test job...")
    job_id = create_test_job(db, test_user_id)
    print(f"✓ Created job: {job_id}")
    
    # Submit to SQS
    print()
    print("📤 Submitting job to SQS...")
    if not submit_job_to_sqs(job_id, queue_url):
        sys.exit(1)
    
    # Monitor job status
    print()
    final_job = monitor_job_status(db, job_id, timeout=300)
    
    if final_job:
        display_job_results(final_job)
        
        # Check agent logs
        print()
        print("📜 Agent Execution Logs:")
        logs = db.agent_logs.find_by_job(job_id)
        for log in logs:
            print(f"   • {log['agent_name']}: {log['status']}")
            if log.get('langfuse_trace_id'):
                print(f"     LangFuse: {log['langfuse_trace_id']}")
    else:
        print("❌ Job monitoring failed")
        sys.exit(1)
    
    # Summary
    print()
    print("=" * 60)
    if final_job and final_job['status'] == 'completed':
        print("✅ Integration test PASSED!")
        print()
        print("The agent orchestration is working correctly:")
        print("  1. Job created in database ✓")
        print("  2. SQS message sent ✓")
        print("  3. Planner Lambda triggered ✓")
        print("  4. Agents coordinated successfully ✓")
        print("  5. Results stored in database ✓")
    else:
        print("❌ Integration test FAILED")
        print()
        print("Troubleshooting:")
        print("  1. Check CloudWatch logs for alex-planner")
        print("  2. Check SQS dead letter queue")
        print("  3. Verify Lambda functions are deployed")
        print("  4. Check IAM permissions")

if __name__ == "__main__":
    main()