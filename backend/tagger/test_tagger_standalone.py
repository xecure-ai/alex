#!/usr/bin/env python3
"""
Standalone test for InstrumentTagger agent.
Tests classification without Lambda deployment.
"""

import asyncio
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import agent functions
from agent import classify_instrument, tag_instruments, classification_to_db_format
from src.models import Database
from src.schemas import InstrumentCreate

# Initialize database
db = Database()

async def test_single_classification():
    """Test classifying a single instrument."""
    print("\n" + "="*60)
    print("TEST 1: Single Instrument Classification")
    print("="*60)
    
    # Test with a well-known ETF
    symbol = "VTI"
    name = "Vanguard Total Stock Market ETF"
    
    print(f"\nClassifying {symbol} - {name}...")
    
    try:
        classification = await classify_instrument(symbol, name, "etf")
        
        print(f"\n✅ Successfully classified {symbol}")
        print(f"  Type: {classification.instrument_type}")
        
        print("\n  Asset Class Allocation:")
        asset_class = classification.allocation_asset_class
        if asset_class.equity > 0: print(f"    - Equity: {asset_class.equity}%")
        if asset_class.fixed_income > 0: print(f"    - Fixed Income: {asset_class.fixed_income}%")
        if asset_class.real_estate > 0: print(f"    - Real Estate: {asset_class.real_estate}%")
        if asset_class.commodities > 0: print(f"    - Commodities: {asset_class.commodities}%")
        if asset_class.cash > 0: print(f"    - Cash: {asset_class.cash}%")
        if asset_class.alternatives > 0: print(f"    - Alternatives: {asset_class.alternatives}%")
        
        # Verify sum is 100
        total = (asset_class.equity + asset_class.fixed_income + asset_class.real_estate + 
                asset_class.commodities + asset_class.cash + asset_class.alternatives)
        print(f"    Total: {total}% {'✅' if abs(total - 100) < 0.01 else '❌'}")
        
        print("\n  Regional Allocation:")
        regions = classification.allocation_regions
        regions_dict = regions.model_dump()
        for region, pct in regions_dict.items():
            if pct > 0:
                print(f"    - {region.replace('_', ' ').title()}: {pct}%")
        
        # Verify sum is 100
        total = sum(regions_dict.values())
        print(f"    Total: {total}% {'✅' if abs(total - 100) < 0.01 else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to classify {symbol}: {e}")
        return False

async def test_multiple_classifications():
    """Test classifying multiple instruments."""
    print("\n" + "="*60)
    print("TEST 2: Multiple Instrument Classification")
    print("="*60)
    
    # Test with various instrument types
    instruments = [
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "instrument_type": "etf"},
        {"symbol": "AAPL", "name": "Apple Inc.", "instrument_type": "stock"},
        {"symbol": "BND", "name": "Vanguard Total Bond Market ETF", "instrument_type": "etf"},
    ]
    
    print(f"\nClassifying {len(instruments)} instruments...")
    
    try:
        classifications = await tag_instruments(instruments)
        
        print(f"\n✅ Successfully classified {len(classifications)} instruments:")
        for classification in classifications:
            print(f"\n  {classification.symbol} - {classification.name}")
            print(f"    Type: {classification.instrument_type}")
            
            # Show dominant allocations
            asset_class = classification.allocation_asset_class
            dominant = []
            if asset_class.equity > 50: dominant.append(f"Equity {asset_class.equity}%")
            if asset_class.fixed_income > 50: dominant.append(f"Fixed Income {asset_class.fixed_income}%")
            if dominant:
                print(f"    Dominant: {', '.join(dominant)}")
        
        return len(classifications) == len(instruments)
        
    except Exception as e:
        print(f"\n❌ Failed to classify instruments: {e}")
        return False

async def test_database_update():
    """Test updating the database with classifications."""
    print("\n" + "="*60)
    print("TEST 3: Database Update")
    print("="*60)
    
    # Use an uncommon symbol for testing
    symbol = "ARKK"
    name = "ARK Innovation ETF"
    
    print(f"\nClassifying and updating {symbol}...")
    
    try:
        # First, classify the instrument
        classification = await classify_instrument(symbol, name, "etf")
        print(f"✅ Classification complete")
        
        # Convert to database format
        db_instrument = classification_to_db_format(classification)
        print(f"✅ Converted to database format")
        
        # Check if it exists in the database
        existing = db.instruments.find_by_symbol(symbol)
        
        if existing:
            # Update existing
            update_data = db_instrument.model_dump()
            del update_data['symbol']  # Remove key field
            
            rows = db.client.update(
                'instruments',
                update_data,
                "symbol = :symbol",
                {'symbol': symbol}
            )
            print(f"✅ Updated {symbol} in database ({rows} rows)")
        else:
            # Create new
            db.instruments.create_instrument(db_instrument)
            print(f"✅ Created {symbol} in database")
        
        # Verify by reading back
        saved = db.instruments.find_by_symbol(symbol)
        if saved:
            print(f"\n✅ Verification: {symbol} exists in database")
            print(f"  - Has asset class data: {bool(saved.get('allocation_asset_class'))}")
            print(f"  - Has regional data: {bool(saved.get('allocation_regions'))}")
            print(f"  - Has sector data: {bool(saved.get('allocation_sectors'))}")
            return True
        else:
            print(f"\n❌ Verification failed: {symbol} not found in database")
            return False
            
    except Exception as e:
        print(f"\n❌ Database update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_lambda_handler_simulation():
    """Test the Lambda handler logic without actual Lambda."""
    print("\n" + "="*60)
    print("TEST 4: Lambda Handler Simulation")
    print("="*60)
    
    # Import the lambda handler's process function
    from lambda_handler import process_instruments
    
    # Prepare test data
    instruments = [
        {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
        {"symbol": "GLD", "name": "SPDR Gold Shares"},
    ]
    
    print(f"\nProcessing {len(instruments)} instruments through handler...")
    
    try:
        result = await process_instruments(instruments)
        
        print(f"\n✅ Handler processed successfully:")
        print(f"  - Tagged: {result['tagged']} instruments")
        print(f"  - Updated: {len(result['updated'])} symbols")
        if result['errors']:
            print(f"  - Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"    • {error['symbol']}: {error['error']}")
        
        # Display classifications
        for classification in result['classifications']:
            print(f"\n  {classification['symbol']}:")
            print(f"    - Type: {classification['type']}")
            
            # Show asset class summary
            asset_class = classification['asset_class']
            dominant = [(k, v) for k, v in asset_class.items() if v > 30]
            if dominant:
                print(f"    - Dominant asset class: {', '.join([f'{k}: {v}%' for k, v in dominant])}")
        
        return result['tagged'] == len(instruments)
        
    except Exception as e:
        print(f"\n❌ Handler simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_missing_allocations():
    """Test identifying and tagging instruments without allocation data."""
    print("\n" + "="*60)
    print("TEST 5: Missing Allocations Detection")
    print("="*60)
    
    # Check for instruments without allocation data
    print("\nChecking database for instruments missing allocations...")
    
    try:
        # Query instruments without allocation data
        all_instruments = db.client.query(
            "SELECT symbol, name, allocation_asset_class, allocation_regions, allocation_sectors FROM instruments"
        )
        
        missing = []
        for inst in all_instruments:
            if not inst.get('allocation_asset_class') or not inst.get('allocation_regions') or not inst.get('allocation_sectors'):
                missing.append({
                    'symbol': inst['symbol'],
                    'name': inst.get('name', '')
                })
        
        if missing:
            print(f"\n⚠️  Found {len(missing)} instruments missing allocations:")
            for inst in missing[:5]:  # Show first 5
                print(f"  - {inst['symbol']}: {inst['name']}")
            
            if len(missing) > 5:
                print(f"  ... and {len(missing) - 5} more")
            
            # Tag the first one as a test
            if missing:
                print(f"\nTagging {missing[0]['symbol']} as a test...")
                classifications = await tag_instruments([missing[0]])
                if classifications:
                    print(f"✅ Successfully tagged {missing[0]['symbol']}")
                    return True
        else:
            print("\n✅ All instruments have allocation data!")
            return True
            
    except Exception as e:
        print(f"\n❌ Missing allocations test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("INSTRUMENTTAGGER STANDALONE TEST SUITE")
    print("="*60)
    
    results = {
        "Single Classification": await test_single_classification(),
        "Multiple Classifications": await test_multiple_classifications(),
        "Database Update": await test_database_update(),
        "Lambda Handler Simulation": await test_lambda_handler_simulation(),
        "Missing Allocations": await test_missing_allocations(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! InstrumentTagger is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)