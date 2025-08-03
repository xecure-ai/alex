"""
Lambda function for ingesting text into OpenSearch with vector embeddings.
"""

import json
import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from botocore.exceptions import ClientError

# Environment variables
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
SAGEMAKER_ENDPOINT = os.environ['SAGEMAKER_ENDPOINT']
INDEX_NAME = os.environ.get('INDEX_NAME', 'alex-knowledge')

# Parse OpenSearch endpoint to get just the hostname
# Remove https:// prefix if present
if OPENSEARCH_ENDPOINT.startswith('https://'):
    OPENSEARCH_HOST = OPENSEARCH_ENDPOINT.replace('https://', '')
elif OPENSEARCH_ENDPOINT.startswith('http://'):
    OPENSEARCH_HOST = OPENSEARCH_ENDPOINT.replace('http://', '')
else:
    OPENSEARCH_HOST = OPENSEARCH_ENDPOINT

# Initialize AWS clients
sagemaker_runtime = boto3.client('sagemaker-runtime')
credentials = boto3.Session().get_credentials()
region = os.environ.get('AWS_REGION', 'us-east-1')

# OpenSearch auth
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    'aoss',  # OpenSearch Serverless uses 'aoss' as service name
    session_token=credentials.token
)

# OpenSearch client
opensearch_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(ClientError),
    before_sleep=lambda retry_state: print(f"SageMaker request failed, retrying (attempt {retry_state.attempt_number + 1}/3)...")
)
def get_embedding(text):
    """
    Get embedding vector from SageMaker endpoint with automatic retry.
    
    Uses tenacity for elegant exponential backoff on cold starts.
    
    Args:
        text: Text to embed
    
    Returns:
        The embedding vector
    """
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    
    result = json.loads(response['Body'].read().decode())
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Expects JSON body with:
    {
        "text": "Text to ingest",
        "metadata": {
            "source": "optional source",
            "category": "optional category"
        }
    }
    """
    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        text = body.get('text')
        metadata = body.get('metadata', {})
        
        if not text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required field: text'})
            }
        
        # Get embedding from SageMaker
        print(f"Getting embedding for text: {text[:100]}...")
        embedding = get_embedding(text)
        
        # Prepare document for OpenSearch
        import datetime
        document = {
            'text': text,
            'embedding': embedding,
            'metadata': metadata,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        # Index the document
        print(f"Indexing document to OpenSearch index: {INDEX_NAME}")
        response = opensearch_client.index(
            index=INDEX_NAME,
            body=document
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document indexed successfully',
                'document_id': response['_id']
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }