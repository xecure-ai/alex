"""
Clean up the Alex OpenSearch database.
This allows you to reset your data and start fresh.
"""

import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path, override=True)

# Get configuration
OPENSEARCH_ENDPOINT = os.getenv('OPENSEARCH_ENDPOINT')
INDEX_NAME = 'alex-knowledge'

if not OPENSEARCH_ENDPOINT:
    print("Error: Please run Guide 3 Step 4 to save OpenSearch configuration to .env")
    exit(1)

# Parse endpoint to get hostname
if OPENSEARCH_ENDPOINT.startswith('https://'):
    OPENSEARCH_HOST = OPENSEARCH_ENDPOINT.replace('https://', '')
else:
    OPENSEARCH_HOST = OPENSEARCH_ENDPOINT

# Setup AWS auth
credentials = boto3.Session().get_credentials()
region = 'us-east-1'
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    'aoss',
    session_token=credentials.token
)

# Create OpenSearch client
client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30
)

def delete_all_documents():
    """Delete all documents from the index but keep the index itself."""
    try:
        # For OpenSearch Serverless, the simplest approach is to delete and recreate the index
        print("Note: OpenSearch Serverless doesn't support bulk delete operations well.")
        print("The most reliable way to clear data is to delete and recreate the index.")
        print()
        
        # Try to delete the index instead
        return delete_index()
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def delete_index():
    """Delete the entire index including its structure."""
    try:
        response = client.indices.delete(index=INDEX_NAME)
        print(f"✓ Deleted entire index '{INDEX_NAME}'")
        print("  A new index will be created automatically when you ingest new documents")
        return True
        
    except Exception as e:
        if "index_not_found_exception" in str(e):
            print(f"✗ Index '{INDEX_NAME}' does not exist - nothing to delete")
        elif "AuthorizationException" in str(e) or "403" in str(e):
            print(f"✗ Permission denied: Unable to delete index")
            print("  This requires the 'aoss:DeleteIndex' permission in the OpenSearch access policy.")
            print("  Update the Terraform configuration and apply changes, then wait 1-2 minutes.")
        else:
            print(f"Error deleting index: {e}")
        return False

def get_document_count():
    """Get the current document count."""
    try:
        count = client.count(index=INDEX_NAME)
        return count['count']
    except:
        return 0

def main():
    """Interactive cleanup tool."""
    print("=" * 60)
    print("Alex OpenSearch Database Cleanup")
    print("=" * 60)
    print(f"Endpoint: {OPENSEARCH_ENDPOINT}")
    print()
    
    # Check current state
    doc_count = get_document_count()
    if doc_count == 0:
        print("ℹ️  Database is already empty (0 documents)")
        return
    
    print(f"⚠️  Current database contains {doc_count} documents")
    print()
    print("What would you like to do?")
    print("1. Delete entire index and all data (recommended)")
    print("2. Cancel (do nothing)")
    print()
    print("Note: OpenSearch Serverless works best with index deletion/recreation")
    print("      rather than individual document deletion.")
    print()
    
    while True:
        choice = input("Enter your choice (1/2): ").strip()
        
        if choice == '1':
            print()
            confirm = input(f"Are you sure you want to delete the index with {doc_count} documents? (yes/no): ").strip().lower()
            if confirm == 'yes':
                delete_index()
            else:
                print("Cancelled - no changes made")
            break
            
        elif choice == '2':
            print("Cancelled - no changes made")
            break
            
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    print()
    print("Done! You can now:")
    print("- Run 'uv run test_api.py' to add new test data")
    print("- Run 'uv run search_api.py' to explore your database")

if __name__ == "__main__":
    main()