#!/usr/bin/env python3
"""Simple test to check database connectivity"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

print("Loading database module...")
from src import Database

print("Creating database instance...")
db = Database()

print("Testing database connection...")
# Try to find a user that doesn't exist
user = db.users.find_by_clerk_id("nonexistent_user")
print(f"User lookup result: {user}")

print("Database connection successful!")