"""
Lambda function to trigger App Runner research endpoint.
Called by EventBridge every 2 hours.
"""
import os
import urllib.request


def handler(event, context):
    """Trigger the research endpoint on App Runner."""
    
    app_runner_url = os.environ.get('APP_RUNNER_URL')
    if not app_runner_url:
        raise ValueError("APP_RUNNER_URL environment variable not set")
    
    url = f"https://{app_runner_url}/research/auto"
    
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=120) as response:
            result = response.read().decode('utf-8')
            
        print(f"Research triggered successfully: {result[:200]}...")
        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        print(f"Error triggering research: {e}")
        return {'statusCode': 500, 'body': str(e)}