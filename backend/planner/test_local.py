#!/usr/bin/env python3
"""
Local test for the planner orchestrator with mocked Lambda invocations.
Tests the agent's ability to coordinate analysis without structured outputs.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

# Enable mock mode for Lambda invocations
os.environ['MOCK_LAMBDAS'] = 'true'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database and create test data
from src.models import Database

db = Database()


def create_test_job():
    """Create a test job in the database."""
    
    # Find or create test user
    test_user_id = 'test_user_local'
    user = db.users.find_by_clerk_id(test_user_id)
    
    if not user:
        logger.info("Creating test user...")
        db.users.create_user(
            clerk_user_id=test_user_id,
            display_name='Test User Local',
            years_until_retirement=25,
            target_retirement_income=100000
        )
    
    # Create test account if it doesn't exist
    accounts = db.accounts.find_by_user(test_user_id)
    if not accounts:
        logger.info("Creating test account and positions...")
        account_id = db.accounts.create_account(
            clerk_user_id=test_user_id,
            account_name='Test 401k',
            account_purpose='retirement',
            cash_balance=5000
        )
        
        # Add some test positions
        try:
            pos1 = db.positions.add_position(account_id, 'SPY', 100)
            logger.info(f"Added SPY position: {pos1}")
            pos2 = db.positions.add_position(account_id, 'QQQ', 50)
            logger.info(f"Added QQQ position: {pos2}")
            pos3 = db.positions.add_position(account_id, 'BND', 75)
            logger.info(f"Added BND position: {pos3}")
            logger.info(f"Created account {account_id} with 3 positions")
        except Exception as e:
            logger.error(f"Error adding positions: {e}")
    else:
        # Log existing positions
        for account in accounts:
            positions = db.positions.find_by_account(account['id'])
            logger.info(f"Account {account['account_name']} has {len(positions)} positions")
    
    # Create a test job
    job_id = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type='portfolio_analysis',
        request_payload={
            'analysis_type': 'full',
            'requested_at': datetime.utcnow().isoformat()
        }
    )
    logger.info(f"Created test job: {job_id}")
    
    return job_id


async def test_planner_local():
    """Test the planner orchestrator locally."""
    
    logger.info("=" * 60)
    logger.info("Testing Planner Orchestrator (Local Mode)")
    logger.info("=" * 60)
    
    # Create test job
    job_id = create_test_job()
    
    # Import and run the orchestrator
    from lambda_handler import run_orchestrator
    
    try:
        logger.info(f"\nRunning orchestrator for job {job_id}...")
        await run_orchestrator(job_id)
        
        # Check the results
        job = db.jobs.find_by_id(job_id)
        
        logger.info("\n" + "=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"Job Status: {job['status']}")
        
        if job.get('summary_payload'):
            logger.info(f"\nOrchestrator Summary:")
            summary = job['summary_payload']
            logger.info(f"  Summary: {summary.get('summary', 'N/A')}")
            logger.info(f"  Key Findings: {summary.get('key_findings', [])}")
            logger.info(f"  Recommendations: {summary.get('recommendations', [])}")
        
        if job.get('report_payload'):
            logger.info(f"\nReport Generated: Yes")
            logger.info(f"  Length: {len(job['report_payload'].get('analysis', ''))} characters")
        
        if job.get('charts_payload'):
            logger.info(f"\nCharts Created: {len(job['charts_payload'])} charts")
            for chart_key in job['charts_payload']:
                logger.info(f"  - {chart_key}")
        
        if job.get('retirement_payload'):
            logger.info(f"\nRetirement Analysis: Yes")
            ret = job['retirement_payload']
            logger.info(f"  Success Rate: {ret.get('success_rate', 'N/A')}%")
        
        if job['status'] == 'completed':
            logger.info("\n✅ Test PASSED - Job completed successfully")
        else:
            logger.error(f"\n❌ Test FAILED - Job status: {job['status']}")
            if job.get('error_message'):
                logger.error(f"Error: {job['error_message']}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def mock_reporter_handler(event, context):
    """Mock reporter Lambda handler for local testing."""
    body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    job_id = body['job_id']
    
    # Simulate reporter saving to database
    db.jobs.update_report(
        job_id=job_id,
        report_payload={
            'analysis': 'This is a mock portfolio analysis report. The portfolio shows good diversification.',
            'generated_at': datetime.utcnow().isoformat()
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'success'})
    }


def mock_charter_handler(event, context):
    """Mock charter Lambda handler for local testing."""
    body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    job_id = body['job_id']
    
    # Simulate charter saving to database
    db.jobs.update_charts(
        job_id=job_id,
        charts_payload={
            'asset_allocation': {
                'title': 'Asset Allocation',
                'type': 'pie',
                'data': [
                    {'name': 'Stocks', 'value': 60, 'percentage': 60},
                    {'name': 'Bonds', 'value': 40, 'percentage': 40}
                ]
            }
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'success'})
    }


def mock_retirement_handler(event, context):
    """Mock retirement Lambda handler for local testing."""
    body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    job_id = body['job_id']
    
    # Simulate retirement saving to database
    db.jobs.update_retirement(
        job_id=job_id,
        retirement_payload={
            'success_rate': 85,
            'projected_value': 2500000,
            'generated_at': datetime.utcnow().isoformat()
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'success'})
    }


# Monkey-patch the mock handlers for MOCK_LAMBDAS mode
if __name__ == "__main__":
    # Override the imports in lambda_handler when MOCK_LAMBDAS is true
    import sys
    import types
    
    # Create mock modules
    mock_reporter = types.ModuleType('backend.reporter.lambda_handler')
    mock_reporter.lambda_handler = mock_reporter_handler
    sys.modules['backend.reporter.lambda_handler'] = mock_reporter
    
    mock_charter = types.ModuleType('backend.charter.lambda_handler')
    mock_charter.lambda_handler = mock_charter_handler
    sys.modules['backend.charter.lambda_handler'] = mock_charter
    
    mock_retirement = types.ModuleType('backend.retirement.lambda_handler')
    mock_retirement.lambda_handler = mock_retirement_handler
    sys.modules['backend.retirement.lambda_handler'] = mock_retirement
    
    # Run the test
    asyncio.run(test_planner_local())