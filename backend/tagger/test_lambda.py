#!/usr/bin/env python3
"""
Test the deployed Lambda function.
"""

import json
import boto3
import time

lambda_client = boto3.client('lambda')

def test_tagger():
    """Test the InstrumentTagger Lambda function."""
    print("Testing InstrumentTagger Lambda...")
    print("-" * 40)
    
    # Test payload
    test_payload = {
        "instruments": [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "instrument_type": "stock"}
        ]
    }
    
    print(f"\nTest payload: {json.dumps(test_payload, indent=2)}")
    
    # Wait a bit for function to be ready
    print("\nWaiting for function to be ready...")
    time.sleep(5)
    
    print("\nInvoking alex-tagger...")
    
    try:
        response = lambda_client.invoke(
            FunctionName='alex-tagger',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())
        
        print(f"\nStatus Code: {status_code}")
        
        if status_code == 200:
            if 'body' in payload:
                body = json.loads(payload['body'])
                print(f"\n✅ Success!")
                print(f"  Tagged: {body.get('tagged', 0)} instruments")
                print(f"  Updated: {body.get('updated', [])}")
                
                # Show classifications
                if 'classifications' in body:
                    print("\nClassifications:")
                    for c in body['classifications']:
                        print(f"\n  {c['symbol']} ({c['name']}):")
                        print(f"    Type: {c['type']}")
                        print(f"    Asset Class: {c.get('asset_class', {})}")
            else:
                print(f"\nResponse: {json.dumps(payload, indent=2)}")
        else:
            print(f"\n❌ Error: {json.dumps(payload, indent=2)}")
            
    except Exception as e:
        print(f"\n❌ Error invoking function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tagger()