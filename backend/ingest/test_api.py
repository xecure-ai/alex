"""
Test script for the Alex API.
This demonstrates how to use the API from Python code.
"""

import os
import requests
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path, override=True)

# Get API configuration from environment
API_ENDPOINT = os.getenv('ALEX_API_ENDPOINT')
API_KEY = os.getenv('ALEX_API_KEY')

if not API_ENDPOINT or not API_KEY:
    print("Error: Please run Guide 3 Step 4 to save API configuration to .env")
    exit(1)

def ingest_document(text, metadata=None, retry=True):
    """
    Ingest a document into the Alex knowledge base.
    
    Args:
        text: The text content to index
        metadata: Optional metadata dictionary
        retry: Whether to retry once on failure
    
    Returns:
        The response from the API
    """
    url = f"{API_ENDPOINT}/ingest"
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        'text': text,
        'metadata': metadata or {}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    # Retry once if we get a SageMaker error (cold start issue)
    if retry and 'error' in result and 'ModelError' in result['error']:
        print("    (Retrying due to model cold start...)")
        import time
        time.sleep(2)  # Wait a bit before retry
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
    
    return result

def main():
    """Test the API with sample data."""
    
    print("Testing Alex API...")
    print(f"Endpoint: {API_ENDPOINT}")
    print()
    
    # Test documents
    test_docs = [
        {
            'text': "Tesla Inc. (TSLA) is an electric vehicle and clean energy company. It designs, manufactures, and sells electric vehicles, energy storage systems, and solar panels.",
            'metadata': {
                'ticker': 'TSLA',
                'company_name': 'Tesla Inc.',
                'sector': 'Automotive/Energy',
                'source': 'portfolio'
            }
        },
        {
            'text': "Amazon.com Inc. (AMZN) is a multinational technology company focusing on e-commerce, cloud computing (AWS), digital streaming, and artificial intelligence.",
            'metadata': {
                'ticker': 'AMZN',
                'company_name': 'Amazon.com Inc.',
                'sector': 'Technology/Retail',
                'source': 'portfolio'
            }
        },
        {
            'text': "NVIDIA Corporation (NVDA) designs graphics processing units (GPUs) for gaming and professional markets, as well as system on chip units for mobile computing and automotive.",
            'metadata': {
                'ticker': 'NVDA',
                'company_name': 'NVIDIA Corporation',
                'sector': 'Technology/Semiconductors',
                'source': 'portfolio'
            }
        }
    ]
    
    # Ingest each document
    for i, doc in enumerate(test_docs, 1):
        print(f"Ingesting document {i}: {doc['metadata'].get('ticker', 'Unknown')}")
        result = ingest_document(doc['text'], doc['metadata'])
        
        if 'document_id' in result:
            print(f"  ✓ Success! Document ID: {result['document_id']}")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")
        print()
    
    print("Testing complete!")
    print("\nYour Alex knowledge base now contains information about:")
    for doc in test_docs:
        print(f"  - {doc['metadata']['company_name']} ({doc['metadata']['ticker']})")
    
    print("\n⏱️  Note: S3 Vectors updates are available immediately.")
    print("   You can run search_api.py right away!")

if __name__ == "__main__":
    main()