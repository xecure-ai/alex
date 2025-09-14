from database.src import Database
import json

db = Database()

# Get the most recent completed job
jobs = db.jobs.find_all()
sorted_jobs = sorted(jobs, key=lambda x: x['created_at'], reverse=True)

# Find first completed job with charter data
for job in sorted_jobs[:5]:
    print(f"\nJob {job['id'][:8]}... - {job['status']} - {job['created_at']}")

    if job.get('charts_payload'):
        print("  Has charts_payload")
        try:
            charts = job['charts_payload']
            if isinstance(charts, str):
                charts = json.loads(charts)

            # Check what's in the charter payload
            if 'content' in charts:
                content = charts['content']
                if isinstance(content, str):
                    # Parse the JSON string
                    chart_data = json.loads(content)
                    print(f"  Chart data keys: {list(chart_data.keys())}")
                    for key, value in chart_data.items():
                        if isinstance(value, list):
                            print(f"    {key}: {len(value)} items")
                        else:
                            print(f"    {key}: {type(value).__name__}")
                else:
                    print(f"  Content type: {type(content).__name__}")
            else:
                print(f"  Charts payload keys: {list(charts.keys())}")
        except Exception as e:
            print(f"  Error parsing charts: {e}")
    else:
        print("  No charts_payload")