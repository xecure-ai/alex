#!/usr/bin/env python3
"""Check if test data exists"""

from src import Database

db = Database()
user = db.users.find_by_clerk_id('test_user_001')
print('User found:', user is not None)
if user:
    accounts = db.accounts.find_by_user('test_user_001')
    print('Accounts:', len(accounts))
    for account in accounts:
        positions = db.positions.find_by_account(account['id'])
        print(f"  Account {account['account_name']}: {len(positions)} positions")