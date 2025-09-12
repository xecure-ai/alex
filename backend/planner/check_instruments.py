#!/usr/bin/env python3
"""Check instruments in database"""

from src import Database

db = Database()

symbols = ['SPY', 'QQQ', 'BND', 'ARKK', 'SOFI', 'VTI', 'GLD']

print("Checking instruments in database:")
print("-" * 50)

for symbol in symbols:
    instrument = db.instruments.find_by_symbol(symbol)
    if instrument:
        has_alloc = bool(instrument.get('allocation_asset_class'))
        print(f"{symbol}: Found - Allocations: {'Yes' if has_alloc else 'No'}")
        if not has_alloc:
            print(f"      Would need tagging")
    else:
        print(f"{symbol}: NOT in database")