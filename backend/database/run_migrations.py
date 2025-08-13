#!/usr/bin/env python3
"""
Simple migration runner that executes statements one by one
"""

import boto3
import json
from pathlib import Path
from botocore.exceptions import ClientError

# Load config
with open('aurora_config.json') as f:
    config = json.load(f)

client = boto3.client('rds-data', region_name=config['region'])

# Read migration file
with open('migrations/001_schema.sql') as f:
    sql = f.read()

# Define statements in order (since splitting is complex)
statements = [
    # Extension
    'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
    
    # Tables
    """CREATE TABLE IF NOT EXISTS users (
        clerk_user_id VARCHAR(255) PRIMARY KEY,
        display_name VARCHAR(255),
        years_until_retirement INTEGER,
        target_retirement_income DECIMAL(12,2),
        asset_class_targets JSONB DEFAULT '{"equity": 70, "fixed_income": 30}',
        region_targets JSONB DEFAULT '{"north_america": 50, "international": 50}',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )""",
    
    """CREATE TABLE IF NOT EXISTS instruments (
        symbol VARCHAR(20) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        instrument_type VARCHAR(50),
        allocation_regions JSONB DEFAULT '{}',
        allocation_sectors JSONB DEFAULT '{}',
        allocation_asset_class JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )""",
    
    """CREATE TABLE IF NOT EXISTS accounts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
        account_name VARCHAR(255) NOT NULL,
        account_purpose TEXT,
        cash_balance DECIMAL(12,2) DEFAULT 0,
        cash_interest DECIMAL(5,4) DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )""",
    
    """CREATE TABLE IF NOT EXISTS positions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
        symbol VARCHAR(20) REFERENCES instruments(symbol),
        quantity DECIMAL(20,8) NOT NULL,
        as_of_date DATE DEFAULT CURRENT_DATE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(account_id, symbol)
    )""",
    
    """CREATE TABLE IF NOT EXISTS price_history (
        symbol VARCHAR(20) REFERENCES instruments(symbol),
        date DATE NOT NULL,
        close_price DECIMAL(12,4) NOT NULL,
        volume BIGINT,
        created_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (symbol, date)
    )""",
    
    """CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
        job_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        request_payload JSONB,
        result_payload JSONB,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP,
        completed_at TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS agent_logs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
        agent_name VARCHAR(100) NOT NULL,
        langfuse_trace_id VARCHAR(255),
        input_tokens INTEGER,
        output_tokens INTEGER,
        execution_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
    )""",
    
    # Indexes
    'CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(clerk_user_id)',
    'CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id)',
    'CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)',
    'CREATE INDEX IF NOT EXISTS idx_price_history_symbol_date ON price_history(symbol, date DESC)',
    'CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(clerk_user_id)',
    'CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)',
    'CREATE INDEX IF NOT EXISTS idx_agent_logs_job ON agent_logs(job_id)',
    
    # Function for timestamps
    """CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql""",
    
    # Triggers
    """CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
    
    """CREATE TRIGGER update_instruments_updated_at BEFORE UPDATE ON instruments
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
    
    """CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
    
    """CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
]

print("🚀 Running database migrations...")
print("=" * 50)

success_count = 0
error_count = 0

for i, stmt in enumerate(statements, 1):
    # Get a description of what we're creating
    stmt_type = "statement"
    if "CREATE TABLE" in stmt.upper():
        stmt_type = "table"
    elif "CREATE INDEX" in stmt.upper():
        stmt_type = "index"
    elif "CREATE TRIGGER" in stmt.upper():
        stmt_type = "trigger"
    elif "CREATE FUNCTION" in stmt.upper():
        stmt_type = "function"
    elif "CREATE EXTENSION" in stmt.upper():
        stmt_type = "extension"
    
    # First non-empty line for display
    first_line = next(l for l in stmt.split('\n') if l.strip())[:60]
    print(f"\n[{i}/{len(statements)}] Creating {stmt_type}...")
    print(f"    {first_line}...")
    
    try:
        response = client.execute_statement(
            resourceArn=config['cluster_arn'],
            secretArn=config['secret_arn'],
            database=config['database'],
            sql=stmt
        )
        print(f"    ✅ Success")
        success_count += 1
        
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        if 'already exists' in error_msg.lower():
            print(f"    ⚠️  Already exists (skipping)")
            success_count += 1
        else:
            print(f"    ❌ Error: {error_msg[:100]}")
            error_count += 1

print("\n" + "=" * 50)
print(f"Migration complete: {success_count} successful, {error_count} errors")

if error_count == 0:
    print("\n✅ All migrations completed successfully!")
    print("\n📝 Next steps:")
    print("1. Load seed data: uv run seed_data.py")
    print("2. Test database operations: uv run test_db.py")
else:
    print(f"\n⚠️  Some statements failed. Check errors above.")