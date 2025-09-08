#!/usr/bin/env python3
"""Check recent job status in database."""

import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

from src.models import Database

db = Database()

# Default to test_user unless specified
user_id = os.getenv('CHECK_USER', 'test_user')

# Get recent jobs
jobs = db.jobs.find_by_user(user_id)

print(f"\n📊 Jobs for user: {user_id}")
print(f"Total jobs: {len(jobs)}")

if not jobs:
    print("No jobs found.")
else:
    print("\n📋 Recent jobs (newest first):")
    print("-" * 70)
    
    for job in reversed(jobs[-10:]):  # Show last 10 jobs, newest first
        status_icon = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        }.get(job['status'], '❓')
        
        created = job.get('created_at', '')
        if created and isinstance(created, str):
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        print(f"{status_icon} {job['id'][:8]}... | {job['status']:10} | {created}")
        
        if job.get('error_message'):
            print(f"   Error: {job['error_message'][:100]}")
    
    # Show details of the most recent job
    print("\n" + "=" * 70)
    print("📄 Most Recent Job Details:")
    print("-" * 70)
    
    latest = jobs[-1]
    print(f"ID: {latest['id']}")
    print(f"Status: {latest['status']}")
    print(f"Created: {latest.get('created_at', 'N/A')}")
    print(f"Updated: {latest.get('updated_at', 'N/A')}")
    
    # Check for results
    has_results = []
    if latest.get('summary_payload'):
        has_results.append('Summary')
    if latest.get('report_payload'):
        has_results.append('Report')
    if latest.get('charts_payload'):
        has_results.append('Charts')
    if latest.get('retirement_payload'):
        has_results.append('Retirement')
    
    if has_results:
        print(f"Results: {', '.join(has_results)}")
    else:
        print("Results: None")
    
    if latest.get('error_message'):
        print(f"\n❌ Error Message:")
        print(f"   {latest['error_message']}")
    
    if latest.get('summary_payload'):
        summary = latest['summary_payload']
        print(f"\n📊 Orchestrator Summary:")
        print(f"   {summary.get('summary', 'N/A')[:200]}...")

print()