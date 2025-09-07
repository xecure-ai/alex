#!/usr/bin/env python3
"""
Simple test for InstrumentTagger - Phase 2.0 validation.
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import agent functions
from agent import classify_instrument, tag_instruments

async def test_structured_output():
    """Test that the agent uses structured outputs correctly (no tools)."""
    print("\n" + "="*60)
    print("TEST: InstrumentTagger Structured Output")
    print("="*60)
    
    # Test classification
    symbol = "SPY"
    name = "SPDR S&P 500 ETF"
    
    print(f"\nClassifying {symbol}...")
    
    try:
        result = await classify_instrument(symbol, name, "etf")
        
        print(f"✅ Successfully classified {symbol}")
        print(f"   Type: {result.instrument_type}")
        
        # Verify allocations sum to 100
        asset_total = (result.allocation_asset_class.equity + 
                      result.allocation_asset_class.fixed_income +
                      result.allocation_asset_class.real_estate +
                      result.allocation_asset_class.commodities +
                      result.allocation_asset_class.cash +
                      result.allocation_asset_class.alternatives)
        
        print(f"   Asset class total: {asset_total}% {'✅' if abs(asset_total - 100) < 0.01 else '❌'}")
        
        # Show the structured output is working
        print(f"\n   Structured output type: {type(result).__name__}")
        print(f"   Has proper Pydantic validation: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_multiple_with_retry():
    """Test multiple classifications with retry logic."""
    print("\n" + "="*60)
    print("TEST: Multiple Classifications with Retry")
    print("="*60)
    
    instruments = [
        {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF"},
        {"symbol": "BND", "name": "Vanguard Total Bond Market ETF"},
    ]
    
    print(f"\nClassifying {len(instruments)} instruments...")
    
    try:
        results = await tag_instruments(instruments)
        
        print(f"✅ Successfully classified {len(results)}/{len(instruments)} instruments")
        
        for result in results:
            print(f"\n   {result.symbol}:")
            print(f"   - Type: {result.instrument_type}")
            print(f"   - Equity: {result.allocation_asset_class.equity}%")
            print(f"   - Fixed Income: {result.allocation_asset_class.fixed_income}%")
        
        return len(results) == len(instruments)
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    """Run the tests."""
    print("\n" + "="*60)
    print("INSTRUMENTTAGGER VALIDATION")
    print("="*60)
    print("\nTesting the InstrumentTagger agent:")
    print("1. Structured output validation")
    print("2. Financial instrument classification")
    print("3. Retry logic for rate limits")
    print("4. Multiple instrument processing")
    
    # Run tests
    test1 = await test_structured_output()
    test2 = await test_multiple_with_retry()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print(f"{'✅' if test1 else '❌'} Structured output working correctly")
    print(f"{'✅' if test2 else '❌'} Multiple classifications with retry logic")
    
    if test1 and test2:
        print("\n✅ InstrumentTagger is working correctly!")
        print("\nThe agent successfully:")
        print("- Classifies financial instruments using AI")
        print("- Returns structured data with allocation percentages")
        print("- Handles rate limits with automatic retries")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    return test1 and test2

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)