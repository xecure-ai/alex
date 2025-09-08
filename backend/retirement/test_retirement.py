"""
Test the Retirement Specialist Agent locally.
"""

import asyncio
import json
import os
from datetime import datetime
from uuid import uuid4

# Set up environment
os.environ['MOCK_DATABASE'] = 'true'  # Use mock database for testing

from lambda_handler import lambda_handler


def create_test_portfolio():
    """Create a realistic test portfolio."""
    return {
        "accounts": [
            {
                "id": str(uuid4()),
                "name": "401(k)",
                "type": "retirement",
                "cash_balance": 15000,
                "positions": [
                    {
                        "symbol": "SPY",
                        "quantity": 150,
                        "instrument": {
                            "name": "SPDR S&P 500 ETF",
                            "current_price": 450,
                            "asset_class": "equity",
                            "allocation_asset_class": {
                                "equity": 100,
                                "fixed_income": 0,
                                "real_estate": 0,
                                "commodities": 0,
                                "cash": 0
                            }
                        }
                    },
                    {
                        "symbol": "BND",
                        "quantity": 200,
                        "instrument": {
                            "name": "Vanguard Total Bond Market ETF",
                            "current_price": 75,
                            "asset_class": "fixed_income",
                            "allocation_asset_class": {
                                "equity": 0,
                                "fixed_income": 100,
                                "real_estate": 0,
                                "commodities": 0,
                                "cash": 0
                            }
                        }
                    },
                    {
                        "symbol": "VNQ",
                        "quantity": 50,
                        "instrument": {
                            "name": "Vanguard Real Estate ETF",
                            "current_price": 85,
                            "asset_class": "real_estate",
                            "allocation_asset_class": {
                                "equity": 0,
                                "fixed_income": 0,
                                "real_estate": 100,
                                "commodities": 0,
                                "cash": 0
                            }
                        }
                    }
                ]
            },
            {
                "id": str(uuid4()),
                "name": "IRA",
                "type": "retirement",
                "cash_balance": 5000,
                "positions": [
                    {
                        "symbol": "QQQ",
                        "quantity": 50,
                        "instrument": {
                            "name": "Invesco QQQ Trust",
                            "current_price": 390,
                            "asset_class": "equity",
                            "allocation_asset_class": {
                                "equity": 100,
                                "fixed_income": 0,
                                "real_estate": 0,
                                "commodities": 0,
                                "cash": 0
                            }
                        }
                    },
                    {
                        "symbol": "AGG",
                        "quantity": 100,
                        "instrument": {
                            "name": "iShares Core US Aggregate Bond ETF",
                            "current_price": 100,
                            "asset_class": "fixed_income",
                            "allocation_asset_class": {
                                "equity": 0,
                                "fixed_income": 100,
                                "real_estate": 0,
                                "commodities": 0,
                                "cash": 0
                            }
                        }
                    }
                ]
            }
        ]
    }


def main():
    """Run the test."""
    print("=" * 60)
    print("Testing Retirement Specialist Agent")
    print("=" * 60)
    
    # Create test job ID (use a valid UUID for testing)
    job_id = str(uuid4())
    print(f"\nJob ID: {job_id}")
    
    # Create test portfolio
    portfolio_data = create_test_portfolio()
    
    # Calculate portfolio value for display
    total_value = sum(
        account['cash_balance'] + 
        sum(pos['quantity'] * pos['instrument']['current_price'] 
            for pos in account['positions'])
        for account in portfolio_data['accounts']
    )
    print(f"Portfolio Value: ${total_value:,.0f}")
    
    # Note: In production, user data is loaded from database
    # For testing, the agent will use defaults:
    # - Years to Retirement: 30
    # - Target Income: $80,000/year
    # - Current Age: 40
    print("Note: Using default user preferences for testing")
    
    # Create event
    event = {
        "job_id": job_id,
        "portfolio_data": portfolio_data
        # user data will be loaded from DB (or defaults in test)
    }
    
    print("\n" + "=" * 60)
    print("Running Retirement Analysis...")
    print("=" * 60)
    
    # Run the lambda handler
    result = lambda_handler(event, None)
    
    # Parse and display results
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        
        if body.get('success'):
            print("\n✓ Analysis completed successfully!")
            print("\nAgent Output:")
            print("-" * 40)
            print(body.get('final_output', 'No output available'))
            
            # Note: The actual analysis data would be stored in the database
            # via the update_job_retirement tool
            print("\n" + "=" * 60)
            print("Note: Full analysis data would be stored in retirement_payload")
            print("in a real environment with database access.")
        else:
            print("\n✗ Analysis failed:")
            print(body.get('error', 'Unknown error'))
    else:
        print(f"\n✗ Request failed with status {result['statusCode']}")
        body = json.loads(result['body'])
        print(f"Error: {body.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()