#!/usr/bin/env python3
"""
Test the database package functionality
"""

from src.models import Database
from decimal import Decimal
import json


def test_database_operations():
    """Test basic database operations"""
    print("🧪 Testing Database Package")
    print("=" * 50)
    
    # Initialize database
    db = Database()
    print("✅ Database initialized")
    
    # Test 1: Query instruments
    print("\n1️⃣ Testing Instruments model...")
    
    # Find by symbol
    spy = db.instruments.find_by_symbol('SPY')
    if spy:
        print(f"   ✅ Found SPY: {spy['name']}")
    else:
        print("   ❌ SPY not found")
    
    # Search instruments
    results = db.instruments.search('Van')
    print(f"   ✅ Search for 'Van' returned {len(results)} results")
    for inst in results[:3]:
        print(f"      • {inst['symbol']}: {inst['name']}")
    
    # Find by type
    bonds = db.instruments.find_by_type('bond_fund')
    print(f"   ✅ Found {len(bonds)} bond funds")
    
    # Test 2: Users operations
    print("\n2️⃣ Testing Users model...")
    
    # Check if test user exists
    test_user = db.users.find_by_clerk_id('test_user_001')
    if test_user:
        print(f"   ✅ Found test user: {test_user['display_name']}")
    else:
        print("   ℹ️  Test user not found (run with --with-test-data)")
    
    # Test 3: Raw queries
    print("\n3️⃣ Testing raw queries...")
    
    # Complex aggregation query
    sql = """
        SELECT 
            instrument_type,
            COUNT(*) as count,
            STRING_AGG(symbol, ', ' ORDER BY symbol) as symbols
        FROM instruments
        GROUP BY instrument_type
        ORDER BY count DESC
        LIMIT 5
    """
    
    results = db.query_raw(sql)
    print(f"   ✅ Aggregation query returned {len(results)} instrument types")
    for row in results:
        print(f"      • {row['instrument_type']}: {row['count']} instruments")
    
    # Test 4: Transaction support
    print("\n4️⃣ Testing transactions...")
    
    try:
        # Begin transaction
        tx_id = db.client.begin_transaction()
        print(f"   ✅ Started transaction: {tx_id[:8]}...")
        
        # Rollback (since we're just testing)
        db.client.rollback_transaction(tx_id)
        print(f"   ✅ Rolled back transaction")
    except Exception as e:
        print(f"   ❌ Transaction test failed: {e}")
    
    # Test 5: Jobs model
    print("\n5️⃣ Testing Jobs model...")
    
    if test_user:
        # Create a test job
        job_id = db.jobs.create_job(
            clerk_user_id='test_user_001',
            job_type='portfolio_analysis',
            request_payload={'test': True}
        )
        print(f"   ✅ Created job: {job_id[:8]}...")
        
        # Update job status
        db.jobs.update_status(job_id, 'running')
        print(f"   ✅ Updated job status to 'running'")
        
        # Complete job
        db.jobs.update_status(
            job_id, 
            'completed',
            result_payload={'analysis': 'test complete'}
        )
        print(f"   ✅ Completed job with results")
        
        # Query user's jobs
        jobs = db.jobs.find_by_user('test_user_001', limit=5)
        print(f"   ✅ User has {len(jobs)} jobs")
    
    # Test 6: Portfolio operations (if test data exists)
    if test_user:
        print("\n6️⃣ Testing Portfolio operations...")
        
        accounts = db.accounts.find_by_user('test_user_001')
        if accounts:
            account = accounts[0]
            print(f"   ✅ Found account: {account['account_name']}")
            
            # Get positions
            positions = db.positions.find_by_account(account['id'])
            print(f"   ✅ Account has {len(positions)} positions")
            
            # Calculate portfolio value
            value_data = db.positions.get_portfolio_value(account['id'])
            if value_data and value_data.get('total_value'):
                print(f"   ✅ Portfolio value: ${value_data['total_value']:,.2f}")
            else:
                print(f"   ℹ️  No price data available for portfolio valuation")
    
    # 7. Testing Pydantic validation
    print("\n7️⃣ Testing Pydantic validation...")
    from src.schemas import InstrumentCreate, PortfolioAnalysis
    from decimal import Decimal
    import json
    
    # Test valid creation
    try:
        valid = InstrumentCreate(
            symbol="TESTVAL",
            name="Validation Test ETF",
            instrument_type="etf",
            allocation_regions={"north_america": 100},
            allocation_sectors={"technology": 100},
            allocation_asset_class={"equity": 100}
        )
        print("   ✅ Valid instrument passes Pydantic validation")
    except Exception as e:
        print(f"   ❌ Unexpected validation error: {e}")
    
    # Test invalid allocations (don't sum to 100)
    try:
        invalid = InstrumentCreate(
            symbol="INVALID",
            name="Invalid ETF",
            instrument_type="etf",
            allocation_regions={"north_america": 60},  # Only 60!
            allocation_sectors={"technology": 100},
            allocation_asset_class={"equity": 100}
        )
        print("   ❌ Should have rejected invalid allocations!")
    except Exception:
        print("   ✅ Invalid allocations correctly rejected")
    
    # Test invalid literal type
    try:
        invalid_type = InstrumentCreate(
            symbol="BADTYPE",
            name="Bad Type ETF",
            instrument_type="invalid_type",  # Not in Literal!
            allocation_regions={"north_america": 100},
            allocation_sectors={"technology": 100},
            allocation_asset_class={"equity": 100}
        )
        print("   ❌ Should have rejected invalid type!")
    except Exception:
        print("   ✅ Invalid literal types correctly rejected")
    
    # Test LLM schema compatibility
    try:
        analysis = PortfolioAnalysis(
            total_value=Decimal("100000"),
            asset_allocation={"equity": 70, "fixed_income": 30},
            region_allocation={"north_america": 60, "international": 40},
            sector_allocation={"technology": 30, "healthcare": 20, "other": 50},
            risk_score=7,
            recommendations=["Rebalance quarterly", "Consider tax loss harvesting"]
        )
        json_output = json.dumps(analysis.model_dump(), default=str)
        print("   ✅ LLM schemas are JSON serializable")
    except Exception as e:
        print(f"   ❌ Schema serialization error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ All database package tests completed!")
    print("\n📝 The database package is ready for use in other services:")
    print("   • Lambda functions can use: uv add --editable ../database")
    print("   • Import with: from src.models import Database")
    print("   • Initialize with: db = Database()")


if __name__ == "__main__":
    test_database_operations()