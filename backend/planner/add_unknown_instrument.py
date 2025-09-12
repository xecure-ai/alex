#!/usr/bin/env python3
"""
Add a position with an unknown instrument to test the tagger workflow
"""

import os
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv(override=True)

from src import Database

db = Database()

# Add a new unknown instrument to the instruments table (no allocation data)
unknown_instrument = {
    'symbol': 'TSLA',
    'name': 'Tesla, Inc.',
    'instrument_type': 'stock',
    'current_price': Decimal('220.00'),
    'allocation_regions': None,  # Missing allocation data
    'allocation_sectors': None,   # Missing allocation data  
    'allocation_asset_class': None  # Missing allocation data
}

try:
    # Insert the instrument
    result = db.instruments.create(unknown_instrument)
    print(f"Added instrument: {result}")
    
    # Get the test user's first account
    accounts = db.accounts.find_by_user('test_user_001')
    if accounts:
        first_account = accounts[0]
        account_id = first_account['id']
        
        # Add a position for this unknown instrument
        position_id = db.positions.add_position(account_id, 'TSLA', Decimal('10'))
        print(f"Added position: 10 shares of TSLA to account {account_id}")
        print(f"Position ID: {position_id}")
        
        # Verify the instrument has no allocation data
        instrument = db.instruments.find_by_symbol('TSLA')
        has_allocations = bool(
            instrument.get("allocation_regions")
            and instrument.get("allocation_sectors")
            and instrument.get("allocation_asset_class")
        )
        print(f"TSLA has allocation data: {has_allocations}")
        
    else:
        print("No accounts found for test_user_001")
        
except Exception as e:
    print(f"Error: {e}")
