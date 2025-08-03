"""
Search and explore the Alex OpenSearch database.
This demonstrates how to query the indexed documents.
"""

import os
import json
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

def check_index():
    """Check if the index exists and get its stats."""
    try:
        # List all indices to see what exists
        all_indices = client.cat.indices(format='json')
        index_found = False
        doc_count = 0
        
        if all_indices:
            print("Existing indices:")
            for idx in all_indices:
                index_name = idx['index']
                docs = idx.get('docs.count', '0')
                print(f"  - {index_name} ({docs} docs)")
                if index_name == INDEX_NAME:
                    index_found = True
                    doc_count = int(docs) if docs else 0
        
        if index_found:
            print(f"\n✓ Index '{INDEX_NAME}' exists with {doc_count} documents")
            if doc_count == 0:
                print("\n⚠️  The index exists but shows 0 documents.")
                print("   This could mean:")
                print("   1. Documents were just added and haven't propagated yet (wait 5-10 seconds)")
                print("   2. The index is empty (run test_api.py to add data)")
            return True
        else:
            print(f"\n✗ Index '{INDEX_NAME}' does not exist yet")
            print("  Run test_api.py first to create and populate the index")
            return False
            
    except Exception as e:
        print(f"Error checking index: {e}")
        return False

def list_all_documents():
    """List all documents in the index."""
    try:
        # Search for all documents
        response = client.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 100,  # Get up to 100 documents
                "_source": {
                    "excludes": ["embedding"]  # Exclude embedding vectors for readability
                }
            }
        )
        
        hits = response['hits']['hits']
        print(f"\nFound {len(hits)} documents in OpenSearch:\n")
        
        for i, hit in enumerate(hits, 1):
            doc = hit['_source']
            metadata = doc.get('metadata', {})
            text_preview = doc.get('text', '')[:100] + '...' if len(doc.get('text', '')) > 100 else doc.get('text', '')
            
            print(f"{i}. Document ID: {hit['_id']}")
            if metadata.get('ticker'):
                print(f"   Ticker: {metadata['ticker']}")
            if metadata.get('company_name'):
                print(f"   Company: {metadata['company_name']}")
            if metadata.get('sector'):
                print(f"   Sector: {metadata['sector']}")
            print(f"   Text: {text_preview}")
            print(f"   Timestamp: {doc.get('timestamp', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"Error listing documents: {e}")

def search_by_text(query):
    """Search for documents by text content."""
    try:
        response = client.search(
            index=INDEX_NAME,
            body={
                "query": {
                    "match": {
                        "text": query
                    }
                },
                "size": 5,
                "_source": {
                    "excludes": ["embedding"]
                }
            }
        )
        
        hits = response['hits']['hits']
        print(f"\nSearch results for '{query}': {len(hits)} matches\n")
        
        for hit in hits:
            doc = hit['_source']
            metadata = doc.get('metadata', {})
            score = hit['_score']
            
            print(f"Score: {score:.2f}")
            if metadata.get('company_name'):
                print(f"Company: {metadata['company_name']} ({metadata.get('ticker', 'N/A')})")
            print(f"Text: {doc.get('text', '')[:200]}...")
            print()
            
    except Exception as e:
        print(f"Error searching: {e}")

def get_index_mapping():
    """Show the index mapping (schema)."""
    try:
        mapping = client.indices.get_mapping(index=INDEX_NAME)
        print("\nIndex Mapping (Schema):")
        print(json.dumps(mapping[INDEX_NAME]['mappings'], indent=2))
    except Exception as e:
        print(f"Error getting mapping: {e}")

def main():
    """Explore the OpenSearch database."""
    print("=" * 60)
    print("Alex OpenSearch Database Explorer")
    print("=" * 60)
    print(f"Endpoint: {OPENSEARCH_ENDPOINT}")
    print()
    
    # Check if index exists
    if not check_index():
        return
    
    # List all documents
    list_all_documents()
    
    # Example searches
    print("=" * 60)
    print("Example Searches")
    print("=" * 60)
    
    # Search for specific terms
    search_terms = ["electric vehicle", "cloud", "gaming"]
    for term in search_terms:
        search_by_text(term)
    
    # Optionally show the schema
    print("\nTo see the index schema, uncomment the next line:")
    # get_index_mapping()

if __name__ == "__main__":
    main()