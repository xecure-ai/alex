#!/usr/bin/env python3
"""
Phase 1: Test and demonstrate the merging pattern for agent results
Shows how each agent should read existing payload and merge their results
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

from src.models import Database

def test_agent_merging_pattern():
    """Demonstrate how agents should merge their results into job payload"""
    
    # Initialize database
    db = Database()
    
    print("Testing Agent Result Merging Pattern")
    print("=" * 50)
    
    # Ensure test user exists
    test_user_id = 'test_merge_user'
    if not db.users.find_by_clerk_id(test_user_id):
        db.users.create_user(clerk_user_id=test_user_id, display_name='Test Merge User')
    
    # Create a test job
    job_id = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type='portfolio_analysis',
        request_payload={'portfolio_id': 'test123'}
    )
    print(f"\nCreated job: {job_id}")
    
    # Simulate Reporter Agent updating results
    print("\n1. Reporter Agent stores its results...")
    
    # First, get existing payload (initially None or empty)
    job = db.jobs.find_by_id(job_id)
    existing_payload = job.get('result_payload', {}) or {}
    
    # Add reporter's results
    existing_payload['report'] = {
        'markdown': '# Portfolio Analysis Report\n\nYour portfolio is well-diversified...',
        'generated_at': datetime.now().isoformat(),
        'word_count': 250
    }
    
    # Update with merged payload
    db.jobs.update_status(job_id, 'running', result_payload=existing_payload)
    print("   ✓ Report stored under 'report' key")
    
    # Simulate Charter Agent updating results
    print("\n2. Charter Agent stores its results...")
    
    # Get current payload
    job = db.jobs.find_by_id(job_id)
    existing_payload = job.get('result_payload', {}) or {}
    
    # Add charter's results
    existing_payload['charts'] = {
        'asset_allocation': {
            'data': [
                {'name': 'Stocks', 'value': 60},
                {'name': 'Bonds', 'value': 30},
                {'name': 'Cash', 'value': 10}
            ]
        },
        'regional_distribution': {
            'data': [
                {'name': 'US', 'value': 50},
                {'name': 'International', 'value': 35},
                {'name': 'Emerging', 'value': 15}
            ]
        }
    }
    
    # Update with merged payload
    db.jobs.update_status(job_id, 'running', result_payload=existing_payload)
    print("   ✓ Charts stored under 'charts' key")
    
    # Simulate Retirement Agent updating results
    print("\n3. Retirement Agent stores its results...")
    
    # Get current payload
    job = db.jobs.find_by_id(job_id)
    existing_payload = job.get('result_payload', {}) or {}
    
    # Add retirement's results
    existing_payload['retirement'] = {
        'projections': {
            'success_rate': 0.85,
            'final_value': 1800000,
            'monthly_income': 7500
        },
        'assumptions': {
            'return_rate': 0.07,
            'inflation': 0.03,
            'years': 30
        }
    }
    
    # Update with merged payload
    db.jobs.update_status(job_id, 'running', result_payload=existing_payload)
    print("   ✓ Retirement projections stored under 'retirement' key")
    
    # Simulate Planner finalizing the job
    print("\n4. Planner Agent finalizes the job...")
    
    # Get final payload
    job = db.jobs.find_by_id(job_id)
    existing_payload = job.get('result_payload', {}) or {}
    
    # Add summary
    existing_payload['summary'] = {
        'agents_called': ['reporter', 'charter', 'retirement'],
        'total_time_seconds': 45,
        'status': 'success'
    }
    
    # Mark as completed
    db.jobs.update_status(job_id, 'completed', result_payload=existing_payload)
    print("   ✓ Job completed with all agent results merged")
    
    # Verify final state
    print("\n" + "=" * 50)
    print("Final Job State:")
    
    final_job = db.jobs.find_by_id(job_id)
    if final_job and final_job.get('result_payload'):
        payload = final_job['result_payload']
        
        print(f"  Status: {final_job['status']}")
        print(f"  Result keys: {list(payload.keys())}")
        
        # Verify all agent results are present
        expected_keys = ['report', 'charts', 'retirement', 'summary']
        for key in expected_keys:
            if key in payload:
                print(f"  ✓ {key}: Present")
            else:
                print(f"  ✗ {key}: Missing")
        
        # Show structure
        print("\n  Payload Structure:")
        print(f"    - report: {len(payload.get('report', {}).get('markdown', ''))} chars")
        print(f"    - charts: {len(payload.get('charts', {}))} chart types")
        print(f"    - retirement: success_rate = {payload.get('retirement', {}).get('projections', {}).get('success_rate')}")
        print(f"    - summary: {payload.get('summary', {}).get('agents_called')}")
    
    # Clean up
    db.jobs.delete(job_id)
    print(f"\n✓ Cleaned up test job: {job_id}")
    
    print("\n" + "=" * 50)
    print("Key Pattern for Agents:")
    print("1. Each agent reads existing result_payload")
    print("2. Each agent adds its results under a unique key")
    print("3. Each agent updates with the merged payload")
    print("4. No data is lost between agent calls")

if __name__ == "__main__":
    try:
        test_agent_merging_pattern()
        print("\n✅ Merging pattern test completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()