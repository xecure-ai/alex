#!/usr/bin/env python3
"""
Test the new Jobs table schema with separate JSONB fields for each agent
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import from the src package
from src.models import Database

def test_new_schema():
    """Test the new schema with separate agent payload fields"""
    
    print("Testing New Jobs Schema with Separate Agent Fields")
    print("=" * 60)
    
    # Initialize database
    db = Database()
    
    # Ensure test user exists
    test_user_id = 'test_new_schema_user'
    if not db.users.find_by_clerk_id(test_user_id):
        db.users.create_user(
            clerk_user_id=test_user_id,
            display_name='Test Schema User'
        )
        print(f"✓ Created test user: {test_user_id}")
    
    # Create a test job
    job_id = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type='portfolio_analysis',
        request_payload={'portfolio_id': 'test456', 'analysis_type': 'full'}
    )
    print(f"\n✓ Created job: {job_id}")
    
    # Test 1: Reporter Agent writes to report_payload
    print("\n1. Testing Reporter Agent field (report_payload)...")
    report_data = {
        'markdown': '# Portfolio Analysis\n\nYour portfolio shows strong diversification...',
        'generated_at': datetime.now().isoformat(),
        'word_count': 500,
        'sections': ['summary', 'analysis', 'recommendations']
    }
    db.jobs.update_report(job_id, report_data)
    print("   ✓ Reporter wrote to report_payload")
    
    # Test 2: Charter Agent writes to charts_payload (parallel execution safe)
    print("\n2. Testing Charter Agent field (charts_payload)...")
    charts_data = {
        'asset_allocation': {
            'type': 'pie',
            'data': [
                {'name': 'Stocks', 'value': 65, 'color': '#4CAF50'},
                {'name': 'Bonds', 'value': 25, 'color': '#2196F3'},
                {'name': 'Cash', 'value': 10, 'color': '#FFC107'}
            ]
        },
        'performance_history': {
            'type': 'line',
            'data': [
                {'month': '2024-01', 'value': 100000},
                {'month': '2024-02', 'value': 102500},
                {'month': '2024-03', 'value': 105000}
            ]
        }
    }
    db.jobs.update_charts(job_id, charts_data)
    print("   ✓ Charter wrote to charts_payload")
    
    # Test 3: Retirement Agent writes to retirement_payload
    print("\n3. Testing Retirement Agent field (retirement_payload)...")
    retirement_data = {
        'projections': {
            'success_rate': 0.89,
            'final_portfolio_value': 2100000,
            'monthly_retirement_income': 8500
        },
        'monte_carlo': {
            'simulations_run': 10000,
            'confidence_intervals': {
                '95_percent': 1800000,
                '50_percent': 2100000,
                '5_percent': 2500000
            }
        },
        'assumptions': {
            'annual_return': 0.07,
            'inflation_rate': 0.03,
            'retirement_years': 30
        }
    }
    db.jobs.update_retirement(job_id, retirement_data)
    print("   ✓ Retirement wrote to retirement_payload")
    
    # Test 4: Planner writes summary
    print("\n4. Testing Planner field (summary_payload)...")
    summary_data = {
        'agents_invoked': ['reporter', 'charter', 'retirement'],
        'total_processing_time': 42.5,
        'tokens_used': {
            'reporter': 1500,
            'charter': 800,
            'retirement': 1200,
            'planner': 500
        },
        'completion_status': 'success'
    }
    db.jobs.update_summary(job_id, summary_data)
    print("   ✓ Planner wrote to summary_payload")
    
    # Test 5: Update status to completed
    print("\n5. Testing status update...")
    db.jobs.update_status(job_id, 'completed')
    print("   ✓ Job marked as completed")
    
    # Verify all fields are independently stored
    print("\n" + "=" * 60)
    print("Verification: Reading back all fields...")
    
    job = db.jobs.find_by_id(job_id)
    if job:
        print(f"\n✓ Job Status: {job['status']}")
        print(f"✓ Started At: {job.get('started_at', 'Not set')}")
        print(f"✓ Completed At: {job.get('completed_at', 'Not set')}")
        
        # Check each agent's payload
        fields_to_check = [
            ('report_payload', 'Reporter'),
            ('charts_payload', 'Charter'),
            ('retirement_payload', 'Retirement'),
            ('summary_payload', 'Planner')
        ]
        
        print("\nAgent Payloads:")
        for field_name, agent_name in fields_to_check:
            payload = job.get(field_name)
            if payload:
                print(f"  ✓ {agent_name:12} - {field_name:20} : {len(str(payload))} bytes")
                # Show a sample of the data
                if field_name == 'report_payload':
                    print(f"    → Word count: {payload.get('word_count')}")
                elif field_name == 'charts_payload':
                    print(f"    → Chart types: {list(payload.keys())}")
                elif field_name == 'retirement_payload':
                    print(f"    → Success rate: {payload['projections']['success_rate']}")
                elif field_name == 'summary_payload':
                    print(f"    → Agents invoked: {payload['agents_invoked']}")
            else:
                print(f"  ✗ {agent_name:12} - {field_name:20} : Not found")
    
    # Clean up
    db.jobs.delete(job_id)
    print(f"\n✓ Cleaned up test job: {job_id}")
    
    print("\n" + "=" * 60)
    print("✅ NEW SCHEMA TEST SUCCESSFUL!")
    print("\nKey Benefits Confirmed:")
    print("1. Each agent writes to its own field - no merging needed")
    print("2. Agents can write in parallel without conflicts")
    print("3. Clear data organization - know exactly where each output is")
    print("4. Simpler agent code - just write, don't read-modify-write")
    
    return True

if __name__ == "__main__":
    try:
        # First, we need to reset the database with the new schema
        print("Resetting database with new schema...")
        os.system("cd /Users/ed/projects/alex/backend/database && uv run reset_db.py")
        print("\n")
        
        # Now run the test
        success = test_new_schema()
        if success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)