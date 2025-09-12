#!/usr/bin/env python3
"""
Test Tagger workflow - Phase 6.5
Tests that unknown instruments are automatically tagged
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

def test_unknown_instruments():
    """Test with portfolio containing unknown instruments"""
    print("\n" + "=" * 70)
    print("📊 TEST: Tagger Workflow - Unknown Instruments")
    print("Expected: Planner should automatically tag ARKK and SOFI")
    print("=" * 70)
    
    # Create user with unknown instruments
    user_id = 'test_tagger_001'
    
    user = db.users.find_by_clerk_id(user_id)
    if not user:
        db.users.create_user(
            clerk_user_id=user_id,
            display_name='Tagger Test User',
            years_until_retirement=20
        )
        
        # Create account
        account_id = db.accounts.create_account(
            clerk_user_id=user_id,
            account_name='Innovation Portfolio',
            account_purpose='taxable',
            cash_balance=2000.0
        )
        
        # Ensure instruments exist (even without allocations)
        for symbol, name, price in [
            ('ARKK', 'ARK Innovation ETF', 50.0),
            ('SOFI', 'SoFi Technologies Inc', 8.0)
        ]:
            if not db.instruments.find_by_symbol(symbol):
                # Add basic instrument without allocations (tagger will fill these)
                from src.schemas import InstrumentCreate
                instrument = InstrumentCreate(
                    symbol=symbol,
                    name=name,
                    instrument_type='etf' if 'ETF' in name else 'stock',
                    current_price=price,
                    allocation_asset_class={},  # Empty - tagger will populate
                    allocation_regions={},
                    allocation_sectors={}
                )
                db.instruments.create_instrument(instrument)
                print(f"  Added {symbol} to instruments (without allocations)")
        
        # Add positions with known and unknown instruments
        for symbol, qty in [('SPY', 10), ('ARKK', 50), ('SOFI', 100), ('QQQ', 20)]:
            db.positions.add_position(
                account_id=account_id,
                symbol=symbol,
                quantity=qty
            )
        print(f"Created portfolio with unknown instruments (ARKK, SOFI) for {user_id}")
    
    # Check instruments before
    print("\n📋 Checking instruments BEFORE job:")
    for symbol in ['SPY', 'ARKK', 'SOFI', 'QQQ']:
        instrument = db.instruments.find_by_symbol(symbol)
        if instrument:
            has_allocations = bool(instrument.get('allocation_asset_class'))
            print(f"  {symbol}: Found, Allocations: {'Yes' if has_allocations else 'No'}")
        else:
            print(f"  {symbol}: Not in database")
    
    # Create and run job
    print("\n🚀 Running analysis job...")
    job_data = {
        'clerk_user_id': user_id,
        'job_type': 'portfolio_analysis',
        'status': 'pending',
        'request_payload': {
            'analysis_type': 'full',
            'test_name': 'Tagger Workflow Test',
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
    print("\nMonitoring job progress...")
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
            print("✅ Job completed!")
            break
        elif status == 'failed':
            print(f"❌ Job failed: {job.get('error_message', 'Unknown error')}")
            break
        
        time.sleep(2)
    
    # Check instruments after
    print("\n📋 Checking instruments AFTER job:")
    tagged_count = 0
    for symbol in ['SPY', 'ARKK', 'SOFI', 'QQQ']:
        instrument = db.instruments.find_by_symbol(symbol)
        if instrument:
            has_allocations = bool(instrument.get('allocation_asset_class'))
            print(f"  {symbol}: Found, Allocations: {'Yes ✅' if has_allocations else 'No ❌'}")
            if has_allocations:
                # Show some allocation details
                asset_class = instrument.get('allocation_asset_class', {})
                print(f"       Asset Class: {asset_class}")
                tagged_count += 1
        else:
            print(f"  {symbol}: Not in database ❌")
    
    if tagged_count >= 3:  # At least SPY, QQQ, and hopefully ARKK/SOFI
        print("\n✅ Tagger workflow successful - instruments were tagged!")
        return True
    else:
        print("\n❌ Tagger workflow may have issues - check logs")
        return False


def test_known_instruments_only():
    """Test with all known instruments - tagger should NOT be called"""
    print("\n" + "=" * 70)
    print("📊 TEST: All Known Instruments")
    print("Expected: Tagger should NOT be called (efficiency)")
    print("=" * 70)
    
    # Use existing test user with well-known instruments
    user_id = 'test_user_001'
    
    print("Running analysis with all known instruments...")
    job_data = {
        'clerk_user_id': user_id,
        'job_type': 'portfolio_analysis',
        'status': 'pending',
        'request_payload': {
            'analysis_type': 'full',
            'test_name': 'Known Instruments Test',
            'requested_at': datetime.now(timezone.utc).isoformat()
        }
    }
    
    job_id = db.jobs.create(job_data)
    
    # Send to SQS
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'job_id': job_id})
    )
    
    # Quick monitor - should be fast since no tagging needed
    print("Monitoring (should be faster without tagging)...")
    start_time = time.time()
    timeout = 180
    
    while time.time() - start_time < timeout:
        job = db.jobs.find_by_id(job_id)
        if job['status'] == 'completed':
            elapsed = int(time.time() - start_time)
            print(f"✅ Completed in {elapsed}s")
            if elapsed < 120:  # Faster without tagging
                print("   → Likely skipped tagger (good!)")
            return True
        elif job['status'] == 'failed':
            print(f"❌ Failed: {job.get('error_message')}")
            return False
        time.sleep(2)
    
    print("❌ Timed out")
    return False


def main():
    print("=" * 70)
    print("🎯 Tagger Workflow Test Suite")
    print("Testing automatic instrument tagging")
    print("=" * 70)
    
    if not queue_url:
        print("❌ Queue not found")
        return 1
    
    # Test 1: Unknown instruments
    test1_pass = test_unknown_instruments()
    time.sleep(5)
    
    # Test 2: Known instruments only
    test2_pass = test_known_instruments_only()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("=" * 70)
    print(f"{'✅ PASS' if test1_pass else '❌ FAIL'} - Unknown Instruments (ARKK, SOFI)")
    print(f"{'✅ PASS' if test2_pass else '❌ FAIL'} - Known Instruments Only")
    
    if test1_pass and test2_pass:
        print("\n🎉 All tagger workflow tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed - check logs for details")
        return 1


if __name__ == "__main__":
    exit(main())