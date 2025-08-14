#!/usr/bin/env python3
"""
Simple test for the InstrumentTagger agent - one instrument at a time.
"""

import asyncio
from agent import classify_instrument, classification_to_db_format
from src.schemas import InstrumentCreate

async def main():
    print("=" * 60)
    print("InstrumentTagger Simple Test")
    print("=" * 60)
    
    # Test a single ETF
    print("\n🔍 Testing SPY classification...")
    
    result = await classify_instrument(
        symbol="SPY",
        name="SPDR S&P 500 ETF",
        instrument_type="etf"
    )
    
    print(f"\n✅ Classified {result.symbol}:")
    print(f"  Name: {result.name}")
    print(f"  Type: {result.instrument_type}")
    
    # Asset allocation
    print(f"\n  Asset Classes:")
    print(f"    Equity: {result.allocation_asset_class.equity}%")
    print(f"    Fixed Income: {result.allocation_asset_class.fixed_income}%")
    print(f"    Cash: {result.allocation_asset_class.cash}%")
    
    # Regional allocation
    print(f"\n  Regions:")
    print(f"    North America: {result.allocation_regions.north_america}%")
    print(f"    Europe: {result.allocation_regions.europe}%")
    print(f"    Asia: {result.allocation_regions.asia}%")
    print(f"    Global: {result.allocation_regions.global_}%")
    
    # Top sectors
    print(f"\n  Top Sectors:")
    sectors = result.allocation_sectors
    sector_list = [
        ("Technology", sectors.technology),
        ("Healthcare", sectors.healthcare),
        ("Financials", sectors.financials),
        ("Consumer Discretionary", sectors.consumer_discretionary),
        ("Industrials", sectors.industrials)
    ]
    for name, value in sector_list:
        if value > 0:
            print(f"    {name}: {value}%")
    
    # Test database conversion
    print("\n🔍 Testing database format conversion...")
    db_instrument = classification_to_db_format(result)
    
    # Verify it's valid
    assert isinstance(db_instrument, InstrumentCreate)
    print("  ✅ Successfully converted to InstrumentCreate")
    print(f"  Allocations saved: {len(db_instrument.allocation_sectors)} sectors")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())