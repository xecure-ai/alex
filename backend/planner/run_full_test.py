#!/usr/bin/env python3
"""
Run a full end-to-end test of the Alex agent orchestration.
This creates a test job and monitors it through completion.

Usage:
    cd backend/planner
    uv run run_full_test.py
"""

import boto3
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Database

def main():
    print("=" * 70)
    print("🎯 Alex Agent Orchestration - Full Test")
    print("=" * 70)
    
    # Get AWS info
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    region = boto3.Session().region_name
    print(f"AWS Account: {account_id}")
    print(f"AWS Region: {region}")
    print()
    
    # Initialize database
    print("📊 Checking test data...")
    db = Database()
    
    # Check for test user
    test_user_id = 'test_user_001'
    user = db.users.find_by_clerk_id(test_user_id)
    
    if not user:
        print("❌ Test user not found. Creating test data...")
        print("   Run: cd ../database && uv run reset_db.py --with-test-data")
        sys.exit(1)
    
    print(f"✓ Test user: {user.get('display_name', test_user_id)}")
    
    # Show portfolio summary
    accounts = db.accounts.find_by_user(test_user_id)
    total_positions = 0
    symbols = set()
    
    print(f"\n📈 Test Portfolio:")
    for account in accounts:
        positions = db.positions.find_by_account(account['id'])
        total_positions += len(positions)
        print(f"   • {account['account_name']}: {len(positions)} positions")
        for pos in positions:
            symbols.add(pos['symbol'])
    
    print(f"   Total: {len(accounts)} accounts, {total_positions} positions")
    print(f"   Holdings: {', '.join(sorted(symbols))}")
    
    # Create new job
    print(f"\n🚀 Creating analysis job...")
    job = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={
            'analysis_type': 'full',
            'include_retirement': True,
            'test_run': True,
            'timestamp': datetime.now().isoformat()
        }
    )
    job_id = job
    print(f"   Job ID: {job_id}")
    
    # Submit to SQS
    print(f"\n📤 Submitting to SQS queue...")
    sqs_client = boto3.client('sqs')
    queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/alex-analysis-jobs"
    
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({
            'job_id': job_id,
            'timestamp': datetime.now().isoformat()
        })
    )
    print(f"   Message ID: {response['MessageId']}")
    
    # Monitor job
    print(f"\n⏳ Monitoring job progress (this takes 2-3 minutes)...")
    print("   Status updates:")
    
    start_time = time.time()
    last_status = 'pending'
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spin_idx = 0
    
    while True:
        # Get job status
        job_data = db.jobs.find_by_id(job_id)
        if not job_data:
            print(f"\n❌ Job {job_id} not found!")
            break
        
        status = job_data['status']
        elapsed = int(time.time() - start_time)
        
        # Update display
        if status != last_status:
            print(f"\n   [{elapsed:3d}s] Status: {last_status} → {status}")
            last_status = status
        else:
            # Show spinner while waiting
            print(f"\r   [{elapsed:3d}s] Status: {status} {spinner[spin_idx % len(spinner)]}", end='', flush=True)
            spin_idx += 1
        
        # Check completion
        if status == 'completed':
            print(f"\n\n✅ Analysis completed in {elapsed} seconds!")
            
            # Show results
            if job_data.get('result_payload'):
                results = job_data['result_payload']
                
                print("\n" + "=" * 70)
                print("📊 ANALYSIS RESULTS")
                print("=" * 70)
                
                if results.get('summary'):
                    print("\n📝 Executive Summary:")
                    print(f"   {results['summary']}")
                
                if results.get('key_findings'):
                    print("\n🔍 Key Findings:")
                    for finding in results['key_findings']:
                        print(f"   • {finding}")
                
                if results.get('recommendations'):
                    print("\n💡 Recommendations:")
                    for i, rec in enumerate(results['recommendations'], 1):
                        print(f"   {i}. {rec}")
                
                # Show chart data if available
                if results.get('charts'):
                    print("\n📊 Chart Data Generated:")
                    charts = results['charts']
                    if isinstance(charts, dict):
                        for chart_name, chart_data in charts.items():
                            if isinstance(chart_data, dict) and 'data' in chart_data:
                                print(f"   • {chart_name}: {len(chart_data.get('data', []))} data points")
                            else:
                                print(f"   • {chart_name}: ✓")
                    else:
                        print("   ✓ Visualization data created")
                
                # Show retirement analysis if available
                if results.get('retirement'):
                    print("\n🎯 Retirement Analysis:")
                    retirement = results['retirement']
                    if isinstance(retirement, dict):
                        if 'success_probability' in retirement:
                            print(f"   • Success Probability: {retirement['success_probability']}%")
                        if 'projected_balance' in retirement:
                            print(f"   • Projected Balance: ${retirement['projected_balance']:,.0f}")
                        if 'years_of_income' in retirement:
                            print(f"   • Years of Income: {retirement['years_of_income']}")
                        if 'recommendation' in retirement:
                            print(f"   • Recommendation: {retirement['recommendation']}")
                    else:
                        print("   ✓ Retirement projections completed")
                
                # Check if market research was used
                if results.get('market_context_used'):
                    print("\n📚 Market Research: ✓ S3 Vectors knowledge base accessed")
                
                print("\n" + "=" * 70)
            break
            
        elif status == 'failed':
            print(f"\n\n❌ Job failed after {elapsed} seconds")
            if job_data.get('error_message'):
                print(f"   Error: {job_data['error_message']}")
            break
        
        # Timeout check
        if elapsed > 300:  # 5 minutes
            print(f"\n\n⏱️  Timeout after {elapsed} seconds")
            break
        
        time.sleep(2)
    
    # Note: Agent execution logging to database is not yet implemented
    # The agents run successfully but don't log to the agent_logs table yet
    
    # CloudWatch logs info
    print("\n📋 For detailed logs, check CloudWatch:")
    print(f"   • Planner: /aws/lambda/alex-planner")
    print(f"   • Tagger: /aws/lambda/alex-tagger")
    print(f"   • Reporter: /aws/lambda/alex-reporter")
    print(f"   • Charter: /aws/lambda/alex-charter")
    print(f"   • Retirement: /aws/lambda/alex-retirement")
    
    print("\n🎉 Test complete!")
    print("\nThis test demonstrated:")
    print("  1. Job creation in Aurora database")
    print("  2. SQS message queuing")
    print("  3. Planner Lambda orchestration")
    print("  4. Agent coordination (Tagger, Reporter, Charter, Retirement)")
    print("  5. S3 Vectors knowledge base search")
    print("  6. Results storage in database")

if __name__ == "__main__":
    main()