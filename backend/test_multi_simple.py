#!/usr/bin/env python3
"""Simple test for multiple accounts"""

import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

print("Starting test...")
print("Loading database module...")

from src import Database

print("Creating database instance...")
db = Database()

# Test user ID
test_user = f"multi_{uuid.uuid4().hex[:8]}"
print(f"Creating test user: {test_user}")

# Create user
db.users.create_user(
    clerk_user_id=test_user,
    display_name="Multi Test",
    years_until_retirement=20
)
print("User created")

# Create 3 accounts
accounts = []
for i in range(1, 4):
    account_id = db.accounts.create_account(
        clerk_user_id=test_user,
        account_name=f"Account {i}",
        account_purpose="test",
        cash_balance=1000.0 * i
    )
    accounts.append(account_id)
    print(f"Created account {i}: {account_id}")

# Check we can find them
found_accounts = db.accounts.find_by_user(test_user)
print(f"Found {len(found_accounts)} accounts for user")

# Clean up
for account_id in accounts:
    db.execute_raw(
        "DELETE FROM accounts WHERE id = :id::uuid",
        [{"name": "id", "value": {"stringValue": account_id}}]
    )

db.execute_raw(
    "DELETE FROM users WHERE clerk_user_id = :user_id",
    [{"name": "user_id", "value": {"stringValue": test_user}}]
)

print("Test completed!")