# Alex Financial Planner SaaS - Development Gameplan

**INTERNAL DOCUMENT - For Development Team Only**

This document outlines the complete plan for building the Alex Financial Planner SaaS platform. This is the roadmap for Parts 5-8 of the course.

## Package Management Strategy (uv)

### Project Structure
- Each folder within `backend/` is a separate uv project with its own `pyproject.toml`
- This enables independent Lambda packaging and service-specific dependencies
- The `backend/database/` package is shared across all services as an editable dependency

### Setup Process for Each Project
```bash
cd backend/[service_name]
uv init --bare              # Create minimal pyproject.toml
uv python pin 3.12          # Pin to Python 3.12 for consistency
uv add --editable ../database  # Add shared database package (for services that need it)
```

### Cross-Platform Approach
- **Always use Python scripts** instead of shell/PowerShell scripts
- Scripts are called with `uv run script_name.py` (works on Mac/Linux/Windows)
- Examples: `package.py` for Lambda packaging, `deploy.py` for deployments, `migrate.py` for database migrations
- This ensures consistent behavior across all operating systems

### Benefits
- Clean dependency isolation per service
- Simplified Lambda packaging (each service packages only its dependencies)
- Consistent database models via shared package
- Cross-platform compatibility without maintaining multiple script versions

## Current State (Parts 1-4 Complete)

### Existing Infrastructure
- ✅ SageMaker Serverless endpoint (embeddings)
- ✅ S3 Vectors for knowledge storage
- ✅ Lambda ingest pipeline
- ✅ App Runner researcher service
- ✅ EventBridge scheduler (optional)
- ✅ API Gateway with API key auth

### What We're Building Next
Transform Alex from a research tool into a complete financial planning SaaS platform with:
- Multi-user support with authentication (Clerk)
- Portfolio management and analysis
- AI-powered financial planning agents
- Interactive frontend (NextJS)
- Full observability and monitoring (LangFuse)

## Database Design

### Schema Overview

```sql
-- Minimal users table (Clerk handles auth)
CREATE TABLE users (
    clerk_user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    years_until_retirement INTEGER,
    target_retirement_income DECIMAL(12,2),  -- Annual income goal
    
    -- Allocation targets for rebalancing
    asset_class_targets JSONB,              -- {"equity": 70, "fixed_income": 30}
    region_targets JSONB                    -- {"north_america": 50, "international": 50}
);

-- Reference data for instruments
CREATE TABLE instruments (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    instrument_type VARCHAR(50),            -- Literal['etf', 'mutual_fund', 'stock', 'bond', 'bond_fund', 'commodity', 'reit']
    
    -- Allocation percentages (0-100) - validated by Pydantic to sum to 100
    allocation_regions JSONB,               -- Keys: north_america, europe, asia, latin_america, africa, middle_east, oceania, global, international
    allocation_sectors JSONB,               -- Keys: technology, healthcare, financials, consumer_discretionary, etc.
    allocation_asset_class JSONB,           -- Keys: equity, fixed_income, real_estate, commodities, cash, alternatives
    
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User's investment accounts
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,     -- "401k", "Roth IRA"
    account_purpose TEXT,                    -- "Long-term retirement savings"
    cash_balance DECIMAL(12,2) DEFAULT 0,   -- Uninvested cash
    cash_interest DECIMAL(5,4) DEFAULT 0,   -- Annual interest rate (0.045 = 4.5%)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Current positions in each account
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) REFERENCES instruments(symbol),
    quantity DECIMAL(20,8) NOT NULL,        -- Supports fractional shares
    as_of_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- AI-generated portfolio reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    report_date DATE DEFAULT CURRENT_DATE,
    
    -- AI-generated content
    report_summary TEXT,                     -- Executive summary
    report_detail TEXT,                      -- Full markdown analysis
    
    -- Chart data for visualization (Recharts format)
    asset_class_chart JSONB,                -- Pie chart data
    region_chart JSONB,                     -- Pie/bar chart data  
    sector_chart JSONB,                     -- Pie/bar chart data
    
    -- Metadata
    generated_by VARCHAR(100),              -- 'alex-analyzer-v1'
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Retirement projections
CREATE TABLE retirement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    
    estimated_income DECIMAL(12,2),         -- Projected annual retirement income
    summary TEXT,                            -- Key insights in markdown
    detail TEXT,                             -- Full analysis in markdown
    chart JSONB,                            -- Projection chart data
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Key Design Decisions
- **Minimal users table** - Clerk handles authentication, we just store FK and preferences
- **JSONB for allocations** - Flexible for different fund structures
- **No cost basis yet** - Keep it simple for MVP, can add later
- **TEXT for markdown** - Agent-generated analysis in markdown format
- **JSONB for charts** - Direct rendering in Recharts/Chart.js

## Technical Architecture

### AI Models
- **Claude 4 Sonnet** via AWS Bedrock for all agents (complex financial analysis)
  - Configurable via environment variable `BEDROCK_MODEL_ID`
  - Default: `anthropic.claude-4-sonnet-20250805-v1:0`
  - Can be changed to other Bedrock models as needed
- **Existing SageMaker** for embeddings (keep as-is)
- **OpenAI Agents SDK** with Bedrock using LiteLLM integration for agent orchestration

### Infrastructure Choices
- **Aurora Serverless v2 PostgreSQL with Data API** - No VPC needed, scales to zero
- **Lambda** for ALL backend services (agents and API)
- **API Gateway** for REST API endpoints with CORS
- **SQS** for async job queue
- **S3 + CloudFront** for static React SPA
- **Clerk** for authentication (client-side only)
- **LangFuse** for observability (native OpenAI Agents SDK support)

### Project Structure
```
alex/
├── terraform/
│   └── modules/
│       ├── rds/              # Database infrastructure
│       ├── cloudfront/       # Frontend CDN
│       └── langfuse/         # Observability (if self-hosted)
│
├── backend/
│   ├── database/            # Shared library (Guide 5) - uv project
│   │   ├── pyproject.toml
│   │   ├── migrations/
│   │   ├── src/alex_database/
│   │   └── tests/
│   │
│   ├── planner/            # Orchestrator (Guide 6) - uv project
│   │   ├── pyproject.toml
│   │   ├── lambda_handler.py  # Lambda with SQS trigger
│   │   ├── package.py
│   │   └── tests/          # Integration tests live here
│   │
│   ├── tagger/             # Instrument tagger (Guide 6) - uv project
│   │   ├── pyproject.toml
│   │   ├── lambda_handler.py  # Populates missing instrument data
│   │   └── package.py
│   │
│   ├── reporter/           # Report agent (Guide 6) - uv project
│   │   ├── pyproject.toml
│   │   ├── lambda_handler.py
│   │   └── package.py
│   │
│   ├── charter/            # Chart agent (Guide 6) - uv project
│   │   ├── pyproject.toml
│   │   ├── lambda_handler.py
│   │   └── package.py
│   │
│   ├── retirement/         # Retirement agent (Guide 6) - uv project
│   │   ├── pyproject.toml
│   │   ├── lambda_handler.py
│   │   └── package.py
│   │
│   └── api/               # Backend API (Guide 7) - uv project
│       ├── pyproject.toml
│       ├── lambda_handler.py  # Lambda + API Gateway
│       └── package.py
│
├── frontend/              # React SPA (Guide 7)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   └── vite.config.ts
│
└── guides/
    ├── 5_database.md
    ├── 6_agents.md
    ├── 7_frontend.md
    └── 8_observability.md
```

## IMPORTANT - Read this - Agent design

For Agents, we will be using OpenAI Agents SDK. This is the name of the production release of what used to be called Swarm.
Each Agent should be its own directory under backend, with its own uv project and lambda function.

The correct package to install is `openai-agents`
`uv add openai-agents`
`uv add "openai-agents[litellm]"`

This code shows idiomatic use of OpenAI Agents SDK with appropriate parameters and use of Structured Ouputs and Tools. This is the approach to be used. Only use Tools and Structured Outputs where they make sense.

BE CAREFUL to consult up to date docs on OpenAI Agents SDK. DO NOT invent arguments like passing in additional parameters to trace(). Check the docs, be up to date.

```python
from pydantic import BaseModel, Field
from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel

class MyResultObject(BaseModel):
    my_field: str = Field(description="Natural language description here")

@function_tool
async def my_tool(arg1: str, arg2: str) -> str:
    """ The docstring here, including listing the args """
    return "result"

async def run_agent():
    model = LitellmModel(model="bedrock/...")
    tools = [my_tool]
    with trace("Clear title of trace - use this thoughtfully - only this one argument"):
        agent = Agent(name="My Agent", instructions="the instructions - import from a separate templates module", model=model, tools=tools)
        result = await Runner.run(agent, input="the task prompt - import from a separate templates module as appropriate", max_turns=20)
    return result.final_output_as(MyResultObject)
```

## Before We Begin: Additional IAM Permissions

Since Part 4, we need additional AWS permissions. Add these to your IAM user's groups or policies:

### Required AWS Managed Policies
- `AmazonRDSDataFullAccess` - For Aurora Data API
- `AWSLambda_FullAccess` - For Lambda functions
- `AmazonSQSFullAccess` - For queue management
- `AmazonEventBridgeFullAccess` - For schedulers
- `CloudFrontFullAccess` - For CDN deployment
- `SecretsManagerReadWrite` - For database credentials

### Custom RDS Policy Required

Create a custom IAM policy named `AlexRDSCustomPolicy` with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RDSPermissions",
            "Effect": "Allow",
            "Action": [
                "rds:CreateDBCluster",
                "rds:CreateDBInstance",
                "rds:CreateDBSubnetGroup",
                "rds:DeleteDBCluster",
                "rds:DeleteDBInstance",
                "rds:DeleteDBSubnetGroup",
                "rds:DescribeDBClusters",
                "rds:DescribeDBInstances",
                "rds:DescribeDBSubnetGroups",
                "rds:ModifyDBCluster",
                "rds:ModifyDBInstance",
                "rds:AddTagsToResource",
                "rds:ListTagsForResource",
                "rds:RemoveTagsFromResource"
            ],
            "Resource": "*"
        },
        {
            "Sid": "EC2Permissions",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress"
            ],
            "Resource": "*"
        },
        {
            "Sid": "SecretsManagerPermissions",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:CreateSecret",
                "secretsmanager:DeleteSecret",
                "secretsmanager:DescribeSecret",
                "secretsmanager:GetSecretValue",
                "secretsmanager:PutSecretValue",
                "secretsmanager:UpdateSecret"
            ],
            "Resource": "*"
        },
        {
            "Sid": "KMSPermissions",
            "Effect": "Allow",
            "Action": [
                "kms:CreateGrant",
                "kms:Decrypt",
                "kms:DescribeKey",
                "kms:Encrypt"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: These permissions are required for Terraform to manage Aurora Serverless v2 resources. The `ListTagsForResource` permission is particularly important for Terraform state management.

## Cost Management Strategy

### Aurora Serverless v2 Costs
- **Running cost**: $1.44-$2.88/day ($43-$87/month)
- **Cannot scale to zero** (unlike v1)
- **Recommendation**: Create, learn, destroy within 3-5 days

### Cost Control Commands
Students can use the included `aurora_cost_management.py` script:

```bash
# From the terraform directory:
cd terraform

# Check current status and costs
uv run aurora_cost_management.py status

# Minimize costs when not actively working (still $1.44/day)
uv run aurora_cost_management.py pause

# Resume for active development
uv run aurora_cost_management.py resume

# COMPLETELY STOP charges (deletes database!)
uv run aurora_cost_management.py destroy

# Recreate after destroy
uv run aurora_cost_management.py recreate
```

### Recommended Timeline
- **Day 1**: Create Aurora, complete Part 5
- **Day 2-3**: Complete Parts 6-7
- **Day 4**: Complete Part 8, capture learnings
- **Day 5**: Destroy Aurora to stop charges
- **Total cost**: ~$7-14 for the entire course

### Additional Permissions Needed
Create a custom policy with:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBCluster",
        "rds:ModifyDBCluster",
        "rds:DeleteDBCluster",
        "rds:DescribeDBClusters"
      ],
      "Resource": "*"
    }
  ]
}
```

✅ **Verify**: Run `aws rds describe-db-clusters` - should return empty list or existing clusters

## Part 5: Database & Shared Infrastructure

### Objective
Set up Aurora Serverless v2 PostgreSQL with Data API and create a reusable database library that all agents can use.

### Steps

1. **Deploy Aurora Serverless v2 with Terraform**
   - Create Aurora cluster with Data API enabled
   - No VPC configuration needed (Data API uses HTTPS)
   - Store credentials in Secrets Manager
   - Configure IAM roles for Lambda access
   - ✅ **Test**: Execute query via AWS CLI using Data API

2. **Create Database Schema**
   - Write SQL migration files (001_schema.sql)
   - Create migration runner script with proper SQL statement splitting
   - Run migrations against Aurora using Data API
   - All JSONB columns validated through Pydantic before insertion
   - ✅ **Test**: Verify all tables exist with correct structure

3. **Build Shared Database Package** (`backend/database/`)
   - Create uv project with Data API client wrapper
   - Implement Pydantic schemas for validation (src/schemas.py)
   - Create database models with automatic type casting
   - Handle JSONB, numeric, date, and UUID type conversions
   - Write comprehensive test suite
   - ✅ **Test**: Run all tests with `uv run test_db.py`

4. **Seed Instruments Table**
   - Create seed data with 22 popular ETFs (SPY, QQQ, BND, etc.)
   - Validate all data through Pydantic InstrumentCreate schema
   - Ensure all allocations sum to 100% with automatic validation
   - ✅ **Test**: Run `uv run seed_data.py`, verify Pydantic validation

5. **Create Database Reset Script** (`backend/database/reset_db.py`)
   - Drop all tables in correct order (handle foreign keys)
   - Recreate schema from migrations
   - Load default instruments (20+ popular ETFs)
   - Optionally create test user with sample portfolio
   - ✅ **Test**: `uv run reset_db.py --with-test-data`

6. **Create Test Data Loader**
   - Script to create test user with sample portfolio
   - Multiple accounts (401k, IRA, Taxable)
   - Various positions across different instruments
   - ✅ **Test**: Load data, query full portfolio

### Pydantic Schema Structure

All database operations use Pydantic schemas for validation:

```python
# backend/database/src/schemas.py

# Literal types for constrained values (LLM-compatible)
RegionType = Literal["north_america", "europe", "asia", ...]
AssetClassType = Literal["equity", "fixed_income", "real_estate", ...]
SectorType = Literal["technology", "healthcare", "financials", ...]

# Input schemas with validation
class InstrumentCreate(BaseModel):
    symbol: str = Field(description="Ticker symbol (e.g., 'SPY')")
    allocation_regions: Dict[RegionType, float]  # Must sum to 100
    allocation_sectors: Dict[SectorType, float]  # Must sum to 100
    allocation_asset_class: Dict[AssetClassType, float]  # Must sum to 100

# Output schemas for LLM structured responses
class PortfolioAnalysis(BaseModel):
    total_value: Decimal
    asset_allocation: Dict[AssetClassType, float]
    risk_score: int = Field(ge=1, le=10)
    recommendations: List[str]
```

### Database Reset Script Structure
```python
# backend/database/reset_db.py
"""
Usage:
  uv run reset_db.py                    # Just load default instruments
  uv run reset_db.py --drop-all        # Drop and recreate all tables
  uv run reset_db.py --with-test-data  # Include test user and portfolio
"""

# Default instruments to always load
DEFAULT_INSTRUMENTS = [
    # Equity ETFs
    {"symbol": "SPY", "name": "SPDR S&P 500", "type": "etf",
     "asset_class": {"equity": 100},
     "regions": {"north_america": 100},
     "sectors": {"technology": 28, "healthcare": 13, "financials": 13, ...}},
    
    # Bond ETFs
    {"symbol": "BND", "name": "Vanguard Total Bond", "type": "etf",
     "asset_class": {"fixed_income": 100},
     "regions": {"north_america": 100},
     "sectors": {"government": 65, "corporate": 35}},
    
    # International
    {"symbol": "VXUS", "name": "Vanguard Total Intl Stock", "type": "etf",
     "asset_class": {"equity": 100},
     "regions": {"europe": 40, "asia": 35, "emerging": 25}},
    
    # Plus 15+ more popular ETFs...
]

# Test portfolio if --with-test-data
TEST_USER = {
    "clerk_user_id": "user_test_123",
    "display_name": "Test User",
    "years_until_retirement": 30,
    "accounts": [
        {"name": "401k", "positions": [
            {"symbol": "SPY", "quantity": 100},
            {"symbol": "BND", "quantity": 200}
        ]},
        {"name": "Roth IRA", "positions": [
            {"symbol": "VXUS", "quantity": 50}
        ]}
    ]
}
```

### Deliverables
- Working Aurora database with Data API
- Shared database package using Data API client
- Database reset script with defaults
- Populated instruments table (20+ ETFs)
- Test data for development

### Acceptance Criteria for Part 5

#### Infrastructure
- [ ] Aurora Serverless v2 cluster is running with Data API enabled
- [ ] Database credentials stored in Secrets Manager
- [ ] Data API endpoint accessible via AWS CLI
- [ ] No VPC or networking configuration required

#### Database Schema
- [ ] All tables created successfully (users, instruments, accounts, positions, reports, retirement, analysis_jobs)
- [ ] Foreign key constraints working properly
- [ ] JSONB columns functioning for flexible data

#### Database Package
- [x] Package installable via `uv add --editable ../database`
- [x] Data API client wrapper handles all operations with automatic type casting
- [x] Pydantic schemas validate all data before database insertion
- [x] Connection uses IAM authentication (no passwords in code)

#### Data Population
- [x] 22 instruments loaded with complete allocation data
- [x] All allocation percentages sum to 100 (validated by Pydantic)
- [x] Test user created with sample portfolio when requested
- [x] Reset script is idempotent (can run multiple times safely)

#### Testing
- [x] Can query database via AWS CLI:
  ```bash
  aws rds-data execute-statement \
    --resource-arn $AURORA_CLUSTER_ARN \
    --secret-arn $AURORA_SECRET_ARN \
    --database alex \
    --sql "SELECT COUNT(*) FROM instruments"
  ```
- [x] Python package can perform CRUD operations
- [x] Reset script completes without errors (`uv run reset_db.py --with-test-data`)
- [x] All tests pass in database package (`uv run test_db.py`)

### Part 5 Completion Summary ✅

**What We Built:**
- Aurora Serverless v2 PostgreSQL cluster with Data API (no VPC complexity)
- Complete database schema with 7 tables
- Shared database package with Pydantic validation
- 22 validated ETF instruments with allocation data
- Comprehensive test suite (3 focused test files)

**Key Features:**
- All data validated through Pydantic schemas before database insertion
- Literal types for constrained values (regions, sectors, asset classes)
- Automatic type casting for JSONB, numeric, date, and UUID fields
- Natural language Field descriptions for LLM compatibility
- Schemas ready for OpenAI/Anthropic function calling

**Files Created:**
```
backend/database/
├── src/                    # Package source
│   ├── client.py          # Data API wrapper with type casting
│   ├── models.py          # Database models
│   └── schemas.py         # Pydantic schemas (LLM-compatible)
├── migrations/            # SQL schema
├── reset_db.py           # Database reset and populate
├── seed_data.py          # Load 22 ETF instruments
├── test_data_api.py      # Initial Aurora setup
├── test_db.py            # Complete test suite
└── verify_database.py    # State verification
```

**Ready for Part 6:** Database is fully operational with clean test output! ✅

---

## Part 6: Agent Orchestra - Core Services

### Objective
Build the AI agent ecosystem where a main orchestrator delegates to specialized agents.

### Steps

1. **Build Financial Planner Agent** (Orchestrator - Lambda)
   - Lambda function with SQS trigger
   - 15 minute timeout, 3GB memory
   - Configurable Bedrock model via `BEDROCK_MODEL_ID` env var
   - Default: `anthropic.claude-4-sonnet-20250805-v1:0`
   - Delegates to other agents via Lambda invocations
   - Calls InstrumentTagger for missing instrument data
   - Has database tools and S3 Vectors access
   - Updates job status in database
   - ✅ **Test**: Local invocation, SQS message processing

2. **Build InstrumentTagger Agent** (Lambda)
   - Simple agent for populating missing instrument reference data
   - Uses Structured Outputs to classify instruments
   - Populates: asset_class, regions, sectors allocations
   - Called by orchestrator when instruments lack data
   - Future enhancement: Add Polygon API tool for real-time data
   - ✅ **Test**: Tag various ETFs and stocks, verify allocations sum to 100

3. **Build Report Writer Agent** (Lambda)
   - Analyzes portfolio data
   - Generates markdown reports
   - Stores in database
   - ✅ **Test**: Invoke with test portfolio, verify markdown output

4. **Build Chart Maker Agent** (Lambda)
   - Creates JSON data for charts
   - Calculates allocations by asset class, region, sector
   - Formats for Recharts
   - ✅ **Test**: Verify JSON structure matches Recharts schema

5. **Build Retirement Specialist Agent** (Lambda)
   - Projects retirement income
   - Monte Carlo simulations
   - Creates projection charts
   - ✅ **Test**: Calculate projections for test user

6. **Integration Testing**
   - Orchestrator calls all agents including InstrumentTagger
   - Complete portfolio analysis flow
   - ✅ **Test**: End-to-end analysis generates full report with charts

### Agent Communication Flow
```
User Request → API → SQS → Planner (Lambda)
                             ├→ InstrumentTagger (Lambda) [if needed]
                             ├→ Report Writer (Lambda)
                             ├→ Chart Maker (Lambda)
                             └→ Retirement Specialist (Lambda)
                                 ↓
                             All results compiled
                                 ↓
                             Stored in Database
                                 ↓
                             Job marked complete
```

### Deliverables
- Working orchestrator Lambda with SQS trigger
- Four specialized Lambda agents (InstrumentTagger, Report Writer, Chart Maker, Retirement)
- Automatic instrument data population
- Full portfolio analysis capability
- Async job processing via SQS

### Acceptance Criteria for Part 6

#### Lambda Infrastructure
- [ ] All 5 Lambda functions deployed (Planner, InstrumentTagger, Reporter, Charter, Retirement)
- [ ] SQS queue created with proper dead letter queue
- [ ] Orchestrator has 15-minute timeout configured
- [ ] All Lambdas have IAM roles with correct permissions
- [ ] Environment variable for BEDROCK_MODEL_ID set

#### Orchestrator Functionality
- [ ] Receives messages from SQS successfully
- [ ] Updates job status in database (pending → running → completed/failed)
- [ ] Invokes other Lambda functions via boto3
- [ ] Handles failures gracefully with error messages
- [ ] Completes full analysis in under 3 minutes

#### InstrumentTagger Agent
- [ ] Identifies instruments missing allocation data
- [ ] Successfully calls Bedrock Claude model
- [ ] Returns structured JSON with allocations
- [ ] All percentages sum to 100
- [ ] Updates database with new data

#### Report Writer Agent  
- [ ] Generates markdown analysis report
- [ ] Includes portfolio summary and recommendations
- [ ] Properly formatted for frontend display
- [ ] Saves to database reports table

#### Chart Maker Agent
- [ ] Calculates portfolio allocations correctly
- [ ] Returns JSON formatted for Recharts
- [ ] Includes asset class, region, and sector breakdowns
- [ ] All chart data percentages sum to 100

#### Retirement Specialist Agent
- [ ] Projects retirement income based on portfolio
- [ ] Generates projection chart data
- [ ] Considers years until retirement
- [ ] Saves analysis to retirement table

#### Integration Testing
- [ ] End-to-end test: Send SQS message → Receive complete analysis
- [ ] Test with portfolio containing unknown instruments
- [ ] Verify all agents called and data stored
- [ ] Job status correctly updated throughout
- [ ] Can handle concurrent job requests

## Part 7: Frontend & Authentication

### Objective
Build a pure client-side React app with Clerk authentication, deployed as a static site to S3/CloudFront, calling API Gateway directly.

### Steps

1. **Deploy API Lambda**
   - Lambda function with API Gateway trigger
   - CORS configuration for browser access (restrict to your domain)
   - JWT validation for Clerk tokens using PyJWT and JWKS
   - Every endpoint verifies the JWT signature with Clerk's public key
   - Extract user_id from validated JWT for row-level security
   - Database operations for portfolios
   - Trigger analysis jobs via SQS
   - ✅ **Test**: API endpoints reject invalid tokens, accept valid ones

2. **Set Up Clerk**
   - Create Clerk application
   - Configure OAuth providers (Google, GitHub)
   - Set up webhook Lambda for user sync to Aurora
   - Get publishable key for frontend
   - Configure allowed origins for CORS
   - ✅ **Test**: Clerk dashboard shows test sign-ups

3. **Build Static React App**
   - Create React app with Vite (faster than CRA)
   - TypeScript for type safety
   - React Router for client-side routing
   - Clerk React SDK for auth
   - No SSR/ISR - pure client-side
   - ✅ **Test**: Dev server runs, auth works locally

4. **Connect Frontend to API**
   - Configure API Gateway endpoint as environment variable
   - Clerk automatically adds JWT to requests
   - Implement API client with fetch
   - Handle CORS preflight requests
   - ✅ **Test**: Browser can call API with auth

5. **Build UI Components**
   - Portfolio input forms
   - Position management
   - Chart components (Recharts)
   - Markdown viewer for reports
   - Loading states and error handling
   - ✅ **Test**: All features work in dev mode

6. **Deploy Static Site to S3/CloudFront**
   - Build production bundle with Vite
   - Upload to S3 bucket (static website hosting)
   - Configure CloudFront distribution
   - Set index.html as default and error document (for SPA routing)
   - ✅ **Test**: Production URL works, auth flows work

### Frontend Pages
- `/` - Landing page
- `/dashboard` - User dashboard
- `/portfolio` - Portfolio management
- `/reports` - View analysis reports
- `/settings` - User preferences

### Deliverables
- API Lambda with API Gateway endpoints + CORS
- Clerk webhook Lambda for user sync
- Pure static React SPA with Clerk auth
- Deployed to S3/CloudFront
- Full CRUD for portfolios
- Agent analysis triggering

### Acceptance Criteria for Part 7

#### API Gateway & CORS Configuration
- [ ] API Gateway REST API deployed with all endpoints
- [ ] CORS headers properly configured:
  - `Access-Control-Allow-Origin`: Your CloudFront domain (NOT *)
  - `Access-Control-Allow-Headers`: Authorization, Content-Type
  - `Access-Control-Allow-Methods`: GET, POST, PUT, DELETE, OPTIONS
- [ ] OPTIONS preflight requests return 200 immediately
- [ ] Test CORS with browser DevTools - no CORS errors
- [ ] API rejects requests from unauthorized origins

#### JWT Authentication
- [ ] Every Lambda validates JWT using Clerk's public keys
- [ ] Invalid tokens return 401 Unauthorized
- [ ] Expired tokens are rejected
- [ ] User ID extracted from token for row-level security
- [ ] Test with curl using invalid token - should fail:
  ```bash
  curl -H "Authorization: Bearer invalid_token" \
    https://api.gateway.url/portfolio
  # Should return 401
  ```

#### Clerk Integration
- [ ] Webhook Lambda processes Clerk user events
- [ ] New users automatically added to database
- [ ] User updates sync to database
- [ ] Frontend gets token via `clerk.session.getToken()`
- [ ] Sign in/out flow works smoothly

#### Frontend Functionality
- [ ] React app builds without errors
- [ ] Routing works for all pages (/dashboard, /portfolio, /reports)
- [ ] API calls include Authorization header automatically
- [ ] Loading states shown during API calls
- [ ] Error states handle API failures gracefully

#### Portfolio Management
- [ ] Create new portfolio positions
- [ ] Update existing positions
- [ ] Delete positions
- [ ] View all accounts and positions
- [ ] Trigger analysis job and get job ID

#### Static Deployment
- [ ] S3 bucket configured for static website hosting
- [ ] CloudFront distribution pointing to S3
- [ ] index.html set as default and error document
- [ ] Cache headers configured appropriately
- [ ] HTTPS enforced via CloudFront

#### End-to-End Testing
- [ ] Sign up new user → User appears in database
- [ ] Add portfolio position → Position saved to database
- [ ] Trigger analysis → Job ID returned → Poll status → Get results
- [ ] Sign out → API calls fail with 401
- [ ] Test from different browser → CORS works correctly

## Part 8: Observability, Monitoring & Security

### Objective
Implement comprehensive observability with LangFuse, monitoring with CloudWatch, and security best practices.

### Steps

1. **Set Up LangFuse**
   - Deploy LangFuse (Docker on ECS or use cloud version)
   - Configure API keys
   - Set up projects for each agent
   - ✅ **Test**: LangFuse UI accessible, API works

2. **Instrument All Agents**
   - Add LangFuse to OpenAI Agents SDK config
   - Trace every agent call
   - Track tool usage
   - Log prompts and completions
   - Track costs per user
   - ✅ **Test**: Traces appear in LangFuse with full detail

3. **Create CloudWatch Dashboards**
   - Agent invocation metrics
   - Database performance
   - API Gateway metrics
   - Cost tracking
   - Error rates
   - ✅ **Test**: All metrics flowing, alerts working

4. **Implement Security Hardening**
   - API rate limiting (API Gateway)
   - Secrets rotation for Aurora credentials
   - WAF rules for CloudFront
   - Least privilege IAM
   - Data API access controls
   - ✅ **Test**: Security scan with OWASP ZAP

5. **Set Up Cost Monitoring**
   - Budget alerts
   - Per-user cost tracking
   - Bedrock usage monitoring
   - Database cost analysis
   - ✅ **Test**: Cost allocation tags working

### Observability Metrics
- Agent execution time
- Tool call frequency
- Token usage per agent
- Error rates by agent
- User session tracking
- Database query performance

### Security Checklist
- [ ] All secrets in Secrets Manager
- [ ] Data API IAM authentication configured
- [ ] API rate limiting enabled
- [ ] WAF rules active
- [ ] IAM roles follow least privilege
- [ ] Database encrypted at rest
- [ ] S3 buckets private
- [ ] CloudTrail enabled

### Deliverables
- Full observability in LangFuse
- CloudWatch dashboards
- Security hardening complete
- Cost tracking operational

### Acceptance Criteria for Part 8

#### LangFuse Integration for Rich Observability
- [ ] LangFuse accessible and configured
- [ ] All agent Lambda functions send detailed traces
- [ ] Orchestrator creates parent trace with:
  - Job metadata (user, portfolio size, job_id)
  - Agent coordination timeline
  - Decision points ("needs tagging", "retirement analysis required")
- [ ] Each agent creates child trace with:
  - Agent persona/role description
  - Reasoning steps (chain of thought)
  - Input/output tokens with cost
  - Execution time and status
  - Custom metadata (e.g., "instruments_tagged": 5)
- [ ] Visual trace hierarchy shows:
  ```
  📊 Portfolio Analysis Job #123
  ├── 🎯 Financial Planner (Orchestrator)
  │   ├── Decision: Missing data for ARKK, SOFI
  │   └── Routing to: InstrumentTagger
  ├── 🏷️ InstrumentTagger 
  │   ├── Tagged: ARKK → Tech ETF (100% equity)
  │   └── Tagged: SOFI → Fintech Stock (100% equity)
  ├── 📝 Report Writer (Parallel)
  │   └── Generated: 2,500 word analysis
  ├── 📊 Chart Maker (Parallel)
  │   └── Created: 3 visualizations
  └── 🎯 Retirement Specialist (Parallel)
      └── Projection: 85% success rate
  ```
- [ ] Traces linked by job_id for correlation
- [ ] Cost breakdown per agent and total
- [ ] Success/failure status clearly visible

#### CloudWatch Monitoring
- [ ] Custom dashboard created with:
  - Lambda invocation counts
  - Lambda error rates
  - API Gateway request counts
  - SQS queue depth
  - Aurora Data API latency
- [ ] Alarms configured for:
  - Lambda errors > 5% 
  - SQS DLQ messages > 0
  - API Gateway 5xx errors
  - Database connection failures
- [ ] Logs properly structured with JSON

#### Security Hardening
- [ ] API Gateway rate limiting enabled (e.g., 100 requests/minute per IP)
- [ ] WAF rules active on CloudFront:
  - SQL injection protection
  - XSS protection
  - Rate limiting
- [ ] All Lambda environment variables use Secrets Manager
- [ ] Database credentials rotated successfully
- [ ] IAM roles follow least privilege principle
- [ ] S3 buckets have versioning enabled
- [ ] CloudTrail logging enabled for audit

#### Cost Controls
- [ ] AWS Budget alert at $50/month
- [ ] Cost allocation tags on all resources:
  - Project: alex
  - Environment: production
  - Owner: [your-name]
- [ ] Per-user cost tracking via LangFuse
- [ ] Aurora auto-pause configured (pause after 5 minutes idle)

#### Performance Validation
- [ ] Lambda cold starts < 2 seconds
- [ ] API response times < 500ms (excluding analysis jobs)
- [ ] Analysis completion < 3 minutes
- [ ] Frontend loads < 2 seconds on 4G connection
- [ ] Database queries < 100ms

#### Security Testing
- [ ] OWASP ZAP scan shows no high-risk vulnerabilities
- [ ] Attempt SQL injection - properly blocked
- [ ] Attempt XSS - properly sanitized
- [ ] Try accessing API without token - returns 401
- [ ] Try accessing another user's data - returns 403

#### Documentation
- [ ] Runbook created for common issues
- [ ] Architecture diagram up to date
- [ ] API documentation complete
- [ ] Cost breakdown documented
- [ ] Security measures documented

## Testing Strategy

### Local Testing at Each Stage

**Guide 5 - Database**
```bash
# Test Aurora Data API connection
aws rds-data execute-statement \
  --resource-arn $AURORA_CLUSTER_ARN \
  --secret-arn $AURORA_SECRET_ARN \
  --database alex \
  --sql "SELECT 1"

# Reset database to clean state
cd backend/database
uv run reset_db.py --drop-all --confirm

# Run migrations
uv run migrations/migrate.py

# Load defaults and test data
uv run reset_db.py --with-test-data

# Test database package
uv run pytest tests/

# Verify data loaded correctly
uv run scripts/verify_data.py
```

**Guide 6 - Agents**
```bash
# Test orchestrator locally
cd backend/planner
uv run test_local.py

# Test InstrumentTagger with unknown symbols
cd backend/tagger
uv run test_local.py --symbol "VTI"
uv run test_local.py --symbol "AAPL"

# Test each Lambda locally
cd backend/reporter
uv run test_local.py

# Integration test (from planner project)
cd backend/planner
uv run tests/test_full_analysis.py
```

**Guide 7 - Frontend**
```bash
# Test Clerk integration
cd frontend
npm run dev
# Complete auth flow in browser

# Test API directly from browser console
fetch('https://api.alex.example.com/portfolio', {
  headers: { 'Authorization': `Bearer ${await clerk.session.getToken()}` }
})

# Test production build
npm run build
npm run preview

# Deploy to S3
aws s3 sync dist/ s3://alex-frontend-bucket --delete

# Test CloudFront deployment
curl https://alex.cloudfront.net
```

**Guide 8 - Observability**
```bash
# Test LangFuse connection (from planner project)
cd backend/planner
uv run tests/test_langfuse.py

# Verify traces
# Check LangFuse UI for detailed traces

# Test CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace "Alex/Agents" \
  --metric-name "InvocationCount" \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum

# Security scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://alex.cloudfront.net
```

## Success Criteria

### Part 5 Success
- [x] Aurora Data API accessible from Lambda (no VPC)
- [x] All tables created with correct schema
- [x] Database package installable in other services
- [x] Test data loads successfully with Pydantic validation

### Part 6 Success
- [ ] Orchestrator delegates to all agents
- [ ] InstrumentTagger populates missing instrument data
- [ ] Each agent produces expected output
- [ ] Full analysis stored in database
- [ ] Charts render correctly in frontend

### Part 7 Success
- [ ] Users can sign up/in via Clerk (client-side)
- [ ] API Gateway CORS configured correctly
- [ ] Portfolio CRUD operations work from browser
- [ ] Agent analysis can be triggered
- [ ] Reports display correctly in React app

### Part 8 Success
- [ ] All agent calls traced in LangFuse
- [ ] CloudWatch dashboards show metrics
- [ ] Security scan passes
- [ ] Costs tracked per user

## CORS Configuration Details

### Critical CORS Setup for API Gateway

Since we're using a static frontend calling API Gateway directly, CORS must be configured perfectly:

#### API Gateway CORS Configuration
```python
# In Terraform for API Gateway
cors_configuration = {
  allow_origins = ["https://your-cloudfront-domain.cloudfront.net"]  # NOT "*"
  allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allow_headers = ["Authorization", "Content-Type"]
  expose_headers = ["x-job-id"]  # For returning job IDs
  max_age = 300
}
```

#### Lambda Response Headers
Every Lambda MUST return CORS headers:
```python
def lambda_handler(event, context):
    # Your logic here
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': 'https://your-domain.cloudfront.net',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(response_data)
    }
```

#### Testing CORS
1. **Browser DevTools Network Tab**:
   - Look for OPTIONS preflight requests
   - Verify they return 200 with CORS headers
   - Check no CORS errors in console

2. **Command Line Test**:
```bash
# Test OPTIONS preflight
curl -X OPTIONS https://api.gateway.url/portfolio \
  -H "Origin: https://your-cloudfront-domain.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" -v

# Should see:
# < Access-Control-Allow-Origin: https://your-cloudfront-domain.cloudfront.net
# < Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS
```

3. **Common CORS Issues**:
   - Missing OPTIONS integration in API Gateway
   - Lambda not returning CORS headers
   - Using * instead of specific domain
   - Forgetting to handle preflight requests

## Risk Mitigation

### Technical Risks
1. **Lambda cold starts** → Use provisioned concurrency for critical paths
2. **Data API throttling** → Implement retry logic with backoff
3. **Bedrock throttling** → Implement exponential backoff
4. **Large portfolios** → Pagination and async processing

### Cost Risks
1. **Bedrock usage** → Set per-user limits
2. **Aurora always running** → Use Aurora Serverless v2 min capacity 0.5 ACU
3. **CloudFront transfer** → Use caching aggressively
4. **LangFuse storage** → Rotate old traces

### Security Risks
1. **API abuse** → Rate limiting and WAF
2. **Data leakage** → Row-level security in database (user_id from JWT)
3. **Token theft** → Short JWT expiry (60s), automatic refresh
4. **SQL injection** → Use parameterized queries only
5. **CORS misconfiguration** → Restrict to specific domain only
6. **Missing JWT validation** → Every Lambda must verify tokens

## Timeline Estimate

### Development Time
- **Part 5**: 1-2 days (Database setup and library)
- **Part 6**: 2-3 days (All agents and integration)
- **Part 7**: 2-3 days (Frontend and deployment)
- **Part 8**: 1-2 days (Observability and security)

**Total**: 6-10 days of development

### Student Time (per guide)
- **Guide 5**: 2-3 hours
- **Guide 6**: 3-4 hours
- **Guide 7**: 3-4 hours
- **Guide 8**: 2-3 hours

**Total**: 10-14 hours for students

## Key Decisions Log

1. **Aurora Serverless v2 with Data API** - No VPC complexity, HTTP-based access
2. **PostgreSQL over DynamoDB** - Need relational queries for portfolio analysis
3. **Clerk over Cognito** - Simpler for students, better DX
4. **CloudFront over Amplify** - More control, standard pattern
5. **LangFuse over CloudWatch** - Better agent-specific observability
6. **Claude 4 Sonnet over OSS** - Superior financial analysis quality
7. **Lambda for all services** - Consistent, simple, no containers
8. **Shared database package** - DRY principle, consistent data access
9. **InstrumentTagger agent** - Auto-populate reference data, reduce manual entry

## Notes for Implementation

### For Ed (Implementation)
- Create database package first - all agents depend on it
- Each backend folder is a separate uv project with its own pyproject.toml
- Database package installed as local dependency: `uv add --editable ../database`
- **Pydantic Integration**:
  - All data validation through Pydantic schemas (not raw JSON)
  - Literal types for constrained values (regions, sectors, asset classes)
  - Natural language Field descriptions for LLM compatibility
  - Automatic type casting in Data API client (JSONB, numeric, date, UUID)
  - Schemas suitable for OpenAI/Anthropic function calling
- Integration tests live in backend/planner/tests/ to avoid dependency issues
- Test Lambda packaging carefully with local dependencies
- Ensure Terraform modules are incremental
- Add cost estimates to each guide
- Include troubleshooting sections
- Make Bedrock model configurable via environment variable in all agents
- Default to Claude 4 Sonnet but allow easy switching

### LangFuse Implementation for Amazing Visualization

Each agent should use OpenAI Agents SDK with LangFuse callback for automatic tracing:

```python
from langfuse.openai import OpenAI
from agents import Agent

# In Orchestrator (creates parent trace)
def lambda_handler(event, context):
    job_id = event['job_id']
    
    langfuse = Langfuse()
    trace = langfuse.trace(
        name="Portfolio Analysis Orchestration",
        user_id=event['user_id'],
        metadata={
            "job_id": job_id,
            "portfolio_value": calculate_total_value(),
            "num_positions": len(positions),
            "agents_to_invoke": ["tagger", "reporter", "charter", "retirement"]
        }
    )
    
    # Each agent call becomes a span
    with trace.span(name="InstrumentTagger Decision"):
        missing = find_missing_instruments()
        if missing:
            trace.event("Routing Decision", {"reason": "Missing instrument data", "symbols": missing})
            invoke_tagger(missing, parent_trace_id=trace.id)

# In each Agent (creates child trace)
def agent_handler(event, context):
    trace = langfuse.trace(
        name="🏷️ InstrumentTagger Agent",
        parent_trace_id=event.get('parent_trace_id'),
        metadata={
            "agent_role": "Classify and tag financial instruments",
            "model": os.environ['BEDROCK_MODEL_ID']
        }
    )
    
    # Rich events for visualization
    for symbol in symbols:
        with trace.span(name=f"Tagging {symbol}"):
            result = classify_instrument(symbol)
            trace.event("Classification Complete", {
                "symbol": symbol,
                "asset_class": result['asset_class'],
                "confidence": result['confidence']
            })
```

Key Features for Impressive LangFuse Display:
1. **Hierarchical traces** - Parent/child relationships show collaboration
2. **Rich metadata** - Portfolio stats, decision points, results
3. **Named spans** - Clear step-by-step within each agent
4. **Events** - Key decisions and milestones
5. **Emojis in trace names** - Visual distinction between agents
6. **Parallel execution visible** - Shows agents running simultaneously
7. **Cost tracking** - Token usage and dollar amounts per agent

### For Students (Guides)
- Each guide should be completable independently
- Include architecture diagrams
- Provide sample data for testing
- Clear success criteria at each step
- Troubleshooting section at the end

## Decisions Made

1. **Data API over direct connections**: No connection pooling complexity
2. **LangFuse**: Cloud version (as long as pricing is reasonable - free tier should suffice)
3. **Custom domain**: Optional but recommended with SSL for professional presentation
4. **Instrument data**: Start with top 20 ETFs, UI allows adding new instruments
   - Future enhancement: Orchestrator could look up tickers via MCP server
5. **Caching layer**: Not for MVP - keep complexity down

## Async Execution Pattern for Long-Running Analysis

### The Challenge
Portfolio analysis takes 2-3 minutes. We need async execution without holding HTTP connections.

### Solution: Job Queue Pattern
1. **Frontend** → POST to API Lambda → Returns job ID immediately
2. **API Lambda** → Creates job record in DB → Sends message to SQS
3. **Orchestrator Lambda** → Triggered by SQS → Runs analysis → Updates job status in DB
4. **Frontend** → Polls job status via API → Shows progress/completion

### Implementation Options

**Our Chosen Approach: SQS + Lambda Orchestrator**
```
Frontend → API Gateway → API Lambda → SQS → Orchestrator Lambda (15 min timeout)
                            ↓                           ↓
                        Return Job ID            Runs full analysis
                                                        ↓
                                                 Updates job in DB
```

This is our chosen approach because:
- Lambda can run for 15 minutes (plenty for 2-3 min analysis)
- Consistent Lambda-only architecture (no Docker/App Runner needed)
- Native SQS integration
- Cost-effective (~$0.10/month)
- Simple for students to understand and deploy

### Database Addition for Async Jobs
```sql
-- Job tracking for async operations
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    request_data JSONB,                   -- Input parameters
    result_data JSONB,                    -- Results when complete
    error_message TEXT,                   -- If failed
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_status ON analysis_jobs(status);
CREATE INDEX idx_jobs_user ON analysis_jobs(clerk_user_id);
```

### Frontend UX Pattern
```typescript
// 1. Trigger analysis
const response = await fetch('/api/analyze', { method: 'POST' });
const { jobId } = await response.json();

// 2. Poll for completion
const pollJob = async (jobId: string) => {
  const res = await fetch(`/api/jobs/${jobId}`);
  const job = await res.json();
  
  if (job.status === 'completed') {
    // Show results
  } else if (job.status === 'failed') {
    // Show error
  } else {
    // Show progress, poll again in 5 seconds
    setTimeout(() => pollJob(jobId), 5000);
  }
};
```

---

*This gameplan will evolve as we build. Each part should be validated before moving to the next.*