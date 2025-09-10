#!/usr/bin/env python3
"""
Full integration test for all deployed Lambda agents.
This tests the complete orchestration flow with real AWS resources.

Prerequisites:
- All Lambda functions deployed (run deploy_all_lambdas.py)
- SQS queue created (alex-analysis-jobs)
- Database with test user (run database/reset_db.py --with-test-data)

Usage:
    cd backend
    uv run test_full.py
"""

import os
import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(cmd, cwd=None):
    """Run a command and capture output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stdout, result.stderr
    return True, result.stdout, result.stderr

def test_deployed_agent(agent_name):
    """Test a deployed agent using its test_full.py if available."""
    agent_dir = Path(__file__).parent / agent_name
    test_file = agent_dir / "test_full.py"
    
    if not test_file.exists():
        print(f"  ⚠️  {agent_name}: No test_full.py, skipping deployed test")
        return True  # Not a failure
    
    print(f"\n{agent_name.upper()} Agent (Deployed):")
    success, stdout, stderr = run_command(
        ['uv', 'run', 'test_full.py'],
        cwd=str(agent_dir)
    )
    
    if success:
        print(f"  ✅ {agent_name}: Deployed test passed")
        # Extract key results
        for line in stdout.split('\n'):
            if 'Job completed' in line or 'Success Rate' in line or 'Charts Created' in line:
                print(f"     {line.strip()}")
    else:
        print(f"  ❌ {agent_name}: Deployed test failed")
        if stderr:
            error_lines = [l for l in stderr.split('\n') if l.strip()]
            if error_lines:
                print(f"     Error: {error_lines[0][:100]}")
    
    return success

def main():
    """Run full integration test."""
    print("="*70)
    print("FULL INTEGRATION TEST - DEPLOYED LAMBDAS")
    print("Testing complete orchestration with AWS resources")
    print("="*70)
    
    # Check prerequisites
    print("\n📋 Checking Prerequisites...")
    
    # Check for .env file
    if not Path('.env').exists() and not Path('../.env').exists():
        print("❌ No .env file found. Please configure environment variables.")
        return 1
    
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")
    
    # Check for AWS credentials
    import boto3
    try:
        sts = boto3.client('sts')
        account = sts.get_caller_identity()
        print(f"✅ AWS Account: {account['Account']}")
        print(f"✅ AWS Region: {boto3.Session().region_name}")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        return 1
    
    # Test the main orchestration flow
    print("\n🚀 Testing Full Orchestration Flow...")
    
    # Run the planner's integration test which tests everything
    planner_dir = Path(__file__).parent / 'planner'
    test_file = planner_dir / 'test_full.py'
    
    if not test_file.exists():
        # Use existing test_integration.py if test_full.py doesn't exist yet
        test_file = planner_dir / 'test_integration.py'
    
    if test_file.exists():
        print("\nRunning complete orchestration test...")
        print("-" * 50)
        
        success, stdout, stderr = run_command(
            ['uv', 'run', test_file.name],
            cwd=str(planner_dir)
        )
        
        if success:
            print("✅ Full orchestration test PASSED!")
            
            # Extract and display key metrics
            print("\n📊 Key Results:")
            for line in stdout.split('\n'):
                if any(keyword in line for keyword in [
                    'Job completed', 'Success Rate', 'Charts', 
                    'Portfolio Report', 'Retirement Analysis',
                    'Key Findings', 'Recommendations'
                ]):
                    print(f"  {line.strip()}")
        else:
            print("❌ Full orchestration test FAILED")
            if stderr:
                print(f"Error: {stderr[:500]}")
            return 1
    else:
        print("❌ No integration test found for planner")
        return 1
    
    # Optional: Test individual deployed agents
    print("\n" + "="*70)
    print("INDIVIDUAL AGENT TESTS (Optional)")
    print("="*70)
    
    agents = ['tagger', 'reporter', 'charter', 'retirement']
    results = {}
    
    for agent in agents:
        # Only run if they have test_full.py
        agent_dir = Path(__file__).parent / agent
        if (agent_dir / 'test_full.py').exists():
            results[agent] = test_deployed_agent(agent)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    print("✅ Main orchestration test: PASSED")
    
    if results:
        passed = sum(1 for r in results.values() if r)
        failed = sum(1 for r in results.values() if not r)
        print(f"\nIndividual agent tests:")
        print(f"  Passed: {passed}/{len(results)}")
        print(f"  Failed: {failed}/{len(results)}")
        
        if failed > 0:
            print("\n  Failed agents:")
            for agent, success in results.items():
                if not success:
                    print(f"    - {agent}")
    
    print("="*70)
    print("\n✅ FULL INTEGRATION TEST COMPLETE!")
    return 0

if __name__ == "__main__":
    sys.exit(main())