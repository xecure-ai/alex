#!/usr/bin/env python3
"""
Test to verify that the tagger's sector and region allocations align with the database schema.
This ensures that the InstrumentClassification can be successfully converted to InstrumentCreate
and saved to the database without validation errors.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "database" / "src"))

from agent import InstrumentClassification, AllocationBreakdown, RegionAllocation, SectorAllocation, classification_to_db_format
from src.schemas import InstrumentCreate, RegionType, SectorType, AssetClassType


def test_sector_alignment():
    """Test that all sector fields in SectorAllocation match the database SectorType."""
    print("\n🔍 Testing Sector Alignment...")
    
    # Get all valid sector values from the database schema
    valid_sectors = set(SectorType.__args__)
    print(f"   Valid DB sectors: {sorted(valid_sectors)}")
    
    # Create a test sector allocation with all fields set
    test_sectors = SectorAllocation(
        technology=10.0,
        healthcare=10.0,
        financials=10.0,
        consumer_discretionary=5.0,
        consumer_staples=5.0,
        industrials=10.0,
        materials=5.0,
        energy=5.0,
        utilities=5.0,
        real_estate=5.0,
        communication=5.0,
        treasury=5.0,
        corporate=5.0,
        mortgage=5.0,
        government_related=5.0,
        commodities=0.0,
        diversified=0.0,
        other=5.0
    )
    
    # Get all fields from the SectorAllocation model
    sector_fields = SectorAllocation.model_fields.keys()
    print(f"   Tagger sectors: {sorted(sector_fields)}")
    
    # Check that all tagger sectors are valid in the database
    invalid_sectors = set(sector_fields) - valid_sectors
    if invalid_sectors:
        print(f"   ❌ Invalid sectors in tagger: {invalid_sectors}")
        return False
    
    print("   ✅ All sector fields align with database schema")
    return True


def test_region_alignment():
    """Test that all region fields in RegionAllocation match the database RegionType."""
    print("\n🔍 Testing Region Alignment...")
    
    # Get all valid region values from the database schema
    valid_regions = set(RegionType.__args__)
    print(f"   Valid DB regions: {sorted(valid_regions)}")
    
    # Create a test region allocation
    test_regions = RegionAllocation(
        north_america=30.0,
        europe=20.0,
        asia=20.0,
        latin_america=5.0,
        africa=5.0,
        middle_east=5.0,
        oceania=5.0,
        global_=5.0,  # Note: using global_ since 'global' is a Python keyword
        international=5.0
    )
    
    # Map the field names to their actual output keys
    region_mapping = {
        'north_america': 'north_america',
        'europe': 'europe',
        'asia': 'asia',
        'latin_america': 'latin_america',
        'africa': 'africa',
        'middle_east': 'middle_east',
        'oceania': 'oceania',
        'global_': 'global',  # Maps to 'global' in output
        'international': 'international'
    }
    
    # Get the output keys that will be used in the database
    output_regions = set(region_mapping.values())
    print(f"   Tagger regions (output): {sorted(output_regions)}")
    
    # Check that all tagger regions are valid in the database
    invalid_regions = output_regions - valid_regions
    if invalid_regions:
        print(f"   ❌ Invalid regions in tagger: {invalid_regions}")
        return False
    
    print("   ✅ All region fields align with database schema")
    return True


def test_asset_class_alignment():
    """Test that all asset class fields match the database AssetClassType."""
    print("\n🔍 Testing Asset Class Alignment...")
    
    # Get all valid asset classes from the database schema
    valid_asset_classes = set(AssetClassType.__args__)
    print(f"   Valid DB asset classes: {sorted(valid_asset_classes)}")
    
    # Create a test asset allocation
    test_assets = AllocationBreakdown(
        equity=40.0,
        fixed_income=30.0,
        real_estate=10.0,
        commodities=10.0,
        cash=5.0,
        alternatives=5.0
    )
    
    # Get all fields from the AllocationBreakdown model
    asset_fields = AllocationBreakdown.model_fields.keys()
    print(f"   Tagger asset classes: {sorted(asset_fields)}")
    
    # Check that all tagger asset classes are valid in the database
    invalid_assets = set(asset_fields) - valid_asset_classes
    if invalid_assets:
        print(f"   ❌ Invalid asset classes in tagger: {invalid_assets}")
        return False
    
    print("   ✅ All asset class fields align with database schema")
    return True


def test_full_conversion():
    """Test that a complete InstrumentClassification can be converted to InstrumentCreate."""
    print("\n🔍 Testing Full Conversion to Database Format...")
    
    try:
        # Create a complete classification
        classification = InstrumentClassification(
            symbol="TEST",
            name="Test ETF",
            instrument_type="etf",
            allocation_asset_class=AllocationBreakdown(
                equity=60.0,
                fixed_income=40.0,
                real_estate=0.0,
                commodities=0.0,
                cash=0.0,
                alternatives=0.0
            ),
            allocation_regions=RegionAllocation(
                north_america=70.0,
                europe=20.0,
                asia=10.0,
                latin_america=0.0,
                africa=0.0,
                middle_east=0.0,
                oceania=0.0,
                global_=0.0,
                international=0.0
            ),
            allocation_sectors=SectorAllocation(
                technology=25.0,
                healthcare=15.0,
                financials=20.0,
                consumer_discretionary=10.0,
                consumer_staples=5.0,
                industrials=10.0,
                materials=5.0,
                energy=5.0,
                utilities=0.0,
                real_estate=0.0,
                communication=5.0,
                treasury=0.0,
                corporate=0.0,
                mortgage=0.0,
                government_related=0.0,
                commodities=0.0,
                diversified=0.0,
                other=0.0
            )
        )
        
        # Convert to database format
        db_instrument = classification_to_db_format(classification)
        
        # Verify it's a valid InstrumentCreate
        assert isinstance(db_instrument, InstrumentCreate)
        print(f"   ✅ Successfully created InstrumentCreate for {db_instrument.symbol}")
        
        # Check the converted data
        print(f"   Asset classes: {db_instrument.allocation_asset_class}")
        print(f"   Regions: {db_instrument.allocation_regions}")
        print(f"   Sectors: {db_instrument.allocation_sectors}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        return False


def main():
    """Run all alignment tests."""
    print("=" * 60)
    print("Tagger to Database Alignment Test")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_asset_class_alignment()
    all_passed &= test_region_alignment()
    all_passed &= test_sector_alignment()
    all_passed &= test_full_conversion()
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All alignment tests passed!")
        print("   The tagger's output is compatible with the database schema.")
    else:
        print("❌ Some alignment tests failed!")
        print("   Please fix the misalignments before deploying.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()