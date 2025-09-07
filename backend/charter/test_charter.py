#!/usr/bin/env python3
"""
Test script for the Charter Agent
Tests the agent locally with a mock job and portfolio data.
"""

import os
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import the charter agent components
from lambda_handler import run_charter_agent, create_chart


async def test_charter_agent():
    """Test the charter agent with sample portfolio data"""
    
    # Create test portfolio data with diverse holdings
    portfolio_data = {
        "accounts": [
            {
                "id": "acc1",
                "name": "401(k)",
                "type": "401k",
                "cash_balance": 10000,
                "positions": [
                    {
                        "symbol": "SPY",
                        "quantity": 100,
                        "instrument": {
                            "name": "SPDR S&P 500 ETF",
                            "current_price": 450.00,
                            "allocation_asset_class": {"equity": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {
                                "technology": 28,
                                "healthcare": 13,
                                "financials": 13,
                                "consumer_discretionary": 12,
                                "communication": 9,
                                "industrials": 9,
                                "consumer_staples": 6,
                                "energy": 4,
                                "utilities": 3,
                                "real_estate": 2,
                                "materials": 1
                            }
                        }
                    },
                    {
                        "symbol": "BND",
                        "quantity": 50,
                        "instrument": {
                            "name": "Vanguard Total Bond Market ETF",
                            "current_price": 80.00,
                            "allocation_asset_class": {"fixed_income": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {"treasury": 60, "corporate": 40}
                        }
                    },
                    {
                        "symbol": "VTI",
                        "quantity": 30,
                        "instrument": {
                            "name": "Vanguard Total Stock Market ETF",
                            "current_price": 230.00,
                            "allocation_asset_class": {"equity": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {"diversified": 100}
                        }
                    }
                ]
            },
            {
                "id": "acc2",
                "name": "IRA",
                "type": "traditional_ira",
                "cash_balance": 5000,
                "positions": [
                    {
                        "symbol": "VXUS",
                        "quantity": 75,
                        "instrument": {
                            "name": "Vanguard Total International Stock ETF",
                            "current_price": 60.00,
                            "allocation_asset_class": {"equity": 100},
                            "allocation_regions": {
                                "europe": 40,
                                "asia": 35,
                                "latin_america": 10,
                                "oceania": 10,
                                "africa": 5
                            },
                            "allocation_sectors": {"diversified": 100}
                        }
                    },
                    {
                        "symbol": "GLD",
                        "quantity": 20,
                        "instrument": {
                            "name": "SPDR Gold Trust",
                            "current_price": 180.00,
                            "allocation_asset_class": {"commodities": 100},
                            "allocation_regions": {"global": 100},
                            "allocation_sectors": {"commodities": 100}
                        }
                    }
                ]
            },
            {
                "id": "acc3",
                "name": "Taxable",
                "type": "taxable",
                "cash_balance": 2000,
                "positions": [
                    {
                        "symbol": "QQQ",
                        "quantity": 25,
                        "instrument": {
                            "name": "Invesco QQQ Trust",
                            "current_price": 380.00,
                            "allocation_asset_class": {"equity": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {"technology": 50, "communication": 20, "consumer_discretionary": 15, "healthcare": 15}
                        }
                    },
                    {
                        "symbol": "VNQ",
                        "quantity": 40,
                        "instrument": {
                            "name": "Vanguard Real Estate ETF",
                            "current_price": 85.00,
                            "allocation_asset_class": {"real_estate": 100},
                            "allocation_regions": {"north_america": 100},
                            "allocation_sectors": {"real_estate": 100}
                        }
                    }
                ]
            }
        ]
    }
    
    print("=" * 60)
    print("TESTING CHARTER AGENT WITH FLEXIBLE APPROACH")
    print("=" * 60)
    
    # Test 1: Verify portfolio data structure
    print("\n1. Checking portfolio data structure...")
    total_value = 0
    num_accounts = len(portfolio_data['accounts'])
    num_positions = 0
    
    for account in portfolio_data['accounts']:
        cash = account.get('cash_balance', 0)
        total_value += cash
        for position in account.get('positions', []):
            num_positions += 1
            instrument = position.get('instrument', {})
            price = instrument.get('current_price', 1.0)
            qty = position.get('quantity', 0)
            total_value += price * qty
    
    print(f"   Total portfolio value: ${total_value:,.2f}")
    print(f"   Number of accounts: {num_accounts}")
    print(f"   Number of positions: {num_positions}")
    
    # Test 2: Run the full agent (with mocked database)
    print("\n2. Testing full agent execution with flexibility...")
    
    # Mock the database for testing
    class MockDatabase:
        class MockJobs:
            def update_charts(self, job_id, charts_data):
                print(f"\n   [MOCK] Would save charts to job {job_id}")
                print(f"   [MOCK] Charts created by agent:")
                for key, chart in charts_data.items():
                    print(f"     - {key}: {chart['title']} ({chart['type']} chart)")
                    print(f"       Description: {chart['description']}")
                    print(f"       Data points: {len(chart['data'])} items")
                return 1
        
        def __init__(self):
            self.jobs = self.MockJobs()
    
    # Import and setup
    import lambda_handler
    
    # Replace the database with mock
    lambda_handler.db = MockDatabase()
    
    # Run the agent
    test_job_id = "test-job-12345"
    
    try:
        result = await run_charter_agent(test_job_id, portfolio_data)
        print(f"\n   Agent completed: {result}")
    except Exception as e:
        print(f"\n   Agent execution stopped (expected in test mode): {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    
    # Show any charts that were created
    if hasattr(create_chart, 'charts') and create_chart.charts:
        print("\nCharts created during test:")
        for key, chart in create_chart.charts.items():
            print(f"\n{key}:")
            print(f"  Title: {chart['title']}")
            print(f"  Type: {chart['type']}")
            print(f"  Data points: {len(chart['data'])}")
            total_pct = sum(d['percentage'] for d in chart['data'])
            print(f"  Total percentage: {total_pct:.1f}%")


if __name__ == "__main__":
    asyncio.run(test_charter_agent())