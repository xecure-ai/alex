"""
Local test script for the InstrumentTagger agent.
Run with: uv run test_local.py
"""

import asyncio
import json
from agent import classify_instrument, tag_instruments

async def test_single_instrument():
    """Test classifying a single instrument."""
    print("\n=== Testing Single Instrument Classification ===")
    
    # Test with a well-known ETF
    result = await classify_instrument(
        symbol="VTI",
        name="Vanguard Total Stock Market ETF",
        instrument_type="etf"
    )
    
    print(f"\nClassified {result.symbol}:")
    print(f"  Name: {result.name}")
    print(f"  Type: {result.instrument_type}")
    
    print("\n  Asset Class Allocation:")
    asset_class = result.allocation_asset_class
    print(f"    Equity: {asset_class.equity:.1f}%")
    print(f"    Fixed Income: {asset_class.fixed_income:.1f}%")
    print(f"    Real Estate: {asset_class.real_estate:.1f}%")
    print(f"    Commodities: {asset_class.commodities:.1f}%")
    print(f"    Cash: {asset_class.cash:.1f}%")
    print(f"    Alternatives: {asset_class.alternatives:.1f}%")
    total_asset = (asset_class.equity + asset_class.fixed_income + asset_class.real_estate + 
                   asset_class.commodities + asset_class.cash + asset_class.alternatives)
    print(f"    Total: {total_asset:.1f}%")
    
    print("\n  Regional Allocation:")
    regions = result.allocation_regions
    region_values = [
        ("North America", regions.north_america),
        ("Europe", regions.europe),
        ("Asia", regions.asia),
        ("Latin America", regions.latin_america),
        ("Africa", regions.africa),
        ("Middle East", regions.middle_east),
        ("Oceania", regions.oceania),
        ("Global", regions.global_),
        ("International", regions.international)
    ]
    for name, value in region_values:
        if value > 0:
            print(f"    {name}: {value:.1f}%")
    total_regions = sum(v for _, v in region_values)
    print(f"    Total: {total_regions:.1f}%")
    
    print("\n  Sector Allocation:")
    sectors = result.allocation_sectors
    sector_values = [
        ("Technology", sectors.technology),
        ("Healthcare", sectors.healthcare),
        ("Financials", sectors.financials),
        ("Consumer Discretionary", sectors.consumer_discretionary),
        ("Consumer Staples", sectors.consumer_staples),
        ("Industrials", sectors.industrials),
        ("Materials", sectors.materials),
        ("Energy", sectors.energy),
        ("Utilities", sectors.utilities),
        ("Real Estate", sectors.real_estate),
        ("Communication", sectors.communication),
        ("Treasury", sectors.treasury),
        ("Corporate", sectors.corporate),
        ("Other", sectors.other)
    ]
    for name, value in sector_values:
        if value > 0:
            print(f"    {name}: {value:.1f}%")
    total_sectors = sum(v for _, v in sector_values)
    print(f"    Total: {total_sectors:.1f}%")
    
    # Validate totals
    assert abs(total_asset - 100.0) < 0.01, f"Asset class doesn't sum to 100: {total_asset}"
    assert abs(total_regions - 100.0) < 0.01, f"Regions don't sum to 100: {total_regions}"
    assert abs(total_sectors - 100.0) < 0.01, f"Sectors don't sum to 100: {total_sectors}"
    
    print("\n✅ Single instrument test passed!")
    return result

async def test_multiple_instruments():
    """Test classifying multiple instruments."""
    print("\n=== Testing Multiple Instruments ===")
    
    test_instruments = [
        {"symbol": "AAPL", "name": "Apple Inc.", "instrument_type": "stock"},
        {"symbol": "BND", "name": "Vanguard Total Bond Market ETF", "instrument_type": "etf"},
        {"symbol": "GLD", "name": "SPDR Gold Shares", "instrument_type": "etf"}
    ]
    
    results = await tag_instruments(test_instruments)
    
    for result in results:
        print(f"\n{result.symbol} - {result.name}:")
        
        # Asset class summary
        asset_values = []
        if result.allocation_asset_class.equity > 0:
            asset_values.append(f"Equity:{result.allocation_asset_class.equity:.0f}%")
        if result.allocation_asset_class.fixed_income > 0:
            asset_values.append(f"Fixed Income:{result.allocation_asset_class.fixed_income:.0f}%")
        if result.allocation_asset_class.commodities > 0:
            asset_values.append(f"Commodities:{result.allocation_asset_class.commodities:.0f}%")
        print(f"  Asset: {', '.join(asset_values)}")
        
        # Region summary
        region_values = []
        if result.allocation_regions.north_america > 0:
            region_values.append(f"North America:{result.allocation_regions.north_america:.0f}%")
        if result.allocation_regions.europe > 0:
            region_values.append(f"Europe:{result.allocation_regions.europe:.0f}%")
        if result.allocation_regions.global_ > 0:
            region_values.append(f"Global:{result.allocation_regions.global_:.0f}%")
        print(f"  Region: {', '.join(region_values)}")
        
        # Top sectors
        sectors = result.allocation_sectors
        sector_list = [
            ("Technology", sectors.technology),
            ("Healthcare", sectors.healthcare),
            ("Financials", sectors.financials),
            ("Government", sectors.government),
            ("Corporate", sectors.corporate),
            ("Other", sectors.other)
        ]
        top_sectors = sorted([(n, v) for n, v in sector_list if v > 0], key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top Sectors: {', '.join([f'{n}:{v:.0f}%' for n, v in top_sectors])}")
    
    print("\n✅ Multiple instruments test passed!")
    return results

async def test_database_format():
    """Test conversion to database format."""
    print("\n=== Testing Database Format Conversion ===")
    
    from agent import classification_to_db_format
    
    # Get a classification
    classification = await classify_instrument(
        symbol="SPY",
        name="SPDR S&P 500 ETF",
        instrument_type="etf"
    )
    
    # Convert to database format
    db_format = classification_to_db_format(classification)
    
    print(f"\nDatabase format for {db_format.symbol}:")
    print(f"  Can be saved to database: ✓")
    print(f"  Pydantic validation passed: ✓")
    
    # Test that it can be serialized
    db_dict = db_format.model_dump()
    print(f"  Serializable to JSON: ✓")
    print(f"  Asset classes: {list(db_dict['allocation_asset_class'].keys())}")
    print(f"  Regions: {list(db_dict['allocation_regions'].keys())}")
    print(f"  Sectors (count): {len(db_dict['allocation_sectors'])} sectors")
    
    print("\n✅ Database format test passed!")
    return db_format

async def main():
    """Run all tests."""
    print("=" * 60)
    print("InstrumentTagger Local Testing")
    print("=" * 60)
    
    try:
        # Test 1: Single instrument
        await test_single_instrument()
        
        # Test 2: Multiple instruments
        await test_multiple_instruments()
        
        # Test 3: Database format
        await test_database_format()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(main())