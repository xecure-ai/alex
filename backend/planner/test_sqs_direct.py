#!/usr/bin/env python3
"""Direct SQS test with immediate job creation and monitoring"""

import os
import json
import boto3
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database

print("=" * 70)
print("🎯 Testing SQS Integration with Planner Lambda")
print("=" * 70)

db = Database()
sqs = boto3.client('sqs')

# Create test job
test_user_id = 'test_user_001'
job_data = {
    'clerk_user_id': test_user_id,
    'job_type': 'portfolio_analysis',
    'status': 'pending',
    'request_payload': {
        'analysis_type': 'full',
        'requested_at': datetime.now(timezone.utc).isoformat(),
        'test_run': True
    }
}

job_id = db.jobs.create(job_data)
print(f"✓ Created job: {job_id}")

# Get queue URL
QUEUE_NAME = 'alex-analysis-jobs'
response = sqs.list_queues(QueueNamePrefix=QUEUE_NAME)
queue_url = None
for url in response.get('QueueUrls', []):
    if QUEUE_NAME in url:
        queue_url = url
        break

if not queue_url:
    print(f"❌ Queue {QUEUE_NAME} not found")
    exit(1)

print(f"✓ Found queue: {queue_url}")

# Send message
response = sqs.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps({'job_id': job_id})
)
print(f"✓ Message sent: {response['MessageId']}")

# Monitor job
print("\n⏳ Monitoring job progress...")
print("-" * 50)

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
        
        if status == 'failed' and job.get('error_message'):
            print(f"       Error: {job.get('error_message')}")
    
    if status == 'completed':
        print("-" * 50)
        print("✅ Job completed successfully!")
        
        # Check what was generated
        if job.get('charts_payload'):
            print(f"📊 Charts created: {len(job['charts_payload'])}")
            for chart_key in list(job['charts_payload'].keys())[:3]:
                print(f"   - {chart_key}")
        else:
            print("❌ No charts found")
            
        if job.get('report_payload'):
            print(f"📝 Report generated: {len(job['report_payload'].get('content', ''))} chars")
        else:
            print("❌ No report found")
            
        break
    elif status == 'failed':
        print("-" * 50)
        print(f"❌ Job failed")
        break
    
    time.sleep(2)
else:
    print("-" * 50)
    print("❌ Job timed out after 3 minutes")
    print(f"Final status: {job['status']}")

print("\nJob ID for debugging:", job_id)