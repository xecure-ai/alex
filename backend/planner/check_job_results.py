#!/usr/bin/env python3
"""Check detailed job results"""

import sys
from src import Database

if len(sys.argv) < 2:
    print("Usage: uv run check_job_results.py <job_id>")
    sys.exit(1)

job_id = sys.argv[1]
db = Database()
job = db.jobs.find_by_id(job_id)

if not job:
    print(f"Job {job_id} not found")
    sys.exit(1)

print(f"Job {job_id} - Status: {job['status']}")
print("=" * 70)

if job.get('charts_payload'):
    print(f"\n📊 Charts Created ({len(job['charts_payload'])} total):")
    print("-" * 50)
    for chart_key, chart_data in job['charts_payload'].items():
        print(f"\n🎯 Chart: {chart_key}")
        print(f"   Title: {chart_data.get('title', 'N/A')}")
        print(f"   Type: {chart_data.get('type', 'N/A')}")
        print(f"   Description: {chart_data.get('description', 'N/A')}")
        print(f"   Data Points: {len(chart_data.get('data', []))}")
        
        # Show first 3 data points
        for i, point in enumerate(chart_data.get('data', [])[:3]):
            name = point.get('name', 'N/A')
            percentage = point.get('percentage', 0)
            color = point.get('color', 'N/A')
            print(f"     {i+1}. {name}: {percentage:.1f}% {color}")
else:
    print("\n❌ No charts found")

if job.get('report_payload'):
    report = job['report_payload']
    print(f"\n📝 Report Generated:")
    print("-" * 50)
    print(f"   Length: {len(report.get('content', ''))} characters")
    print(f"   First line: {report.get('content', '').split('\\n')[0][:100]}...")
else:
    print("\n❌ No report found")

if job.get('retirement_payload'):
    print(f"\n🎯 Retirement Analysis Generated:")
    print("-" * 50)
    print(f"   Projection data included")
else:
    print("\n❌ No retirement analysis found")