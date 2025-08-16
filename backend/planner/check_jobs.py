#!/usr/bin/env python3
"""Check recent job status in database."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Database

db = Database()
jobs = db.jobs.find_by_user('test_user_001')

print(f"\nTotal jobs for test_user_001: {len(jobs)}")
print("\nRecent jobs:")
for job in jobs[-5:]:
    status = job['status']
    error = job.get('error_message', '')
    if error:
        error = f" - Error: {error[:100]}"
    print(f"  {job['id']}: {status}{error}")
    
# Get the most recent job details
if jobs:
    latest = jobs[-1]
    print(f"\nLatest job details:")
    print(f"  ID: {latest['id']}")
    print(f"  Status: {latest['status']}")
    print(f"  Created: {latest['created_at']}")
    if 'updated_at' in latest:
        print(f"  Updated: {latest['updated_at']}")
    if latest.get('result_payload'):
        print(f"  Has results: Yes")
    if latest.get('error_message'):
        print(f"  Error: {latest['error_message']}")