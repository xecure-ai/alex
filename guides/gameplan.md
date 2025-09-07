# Alex Financial Planner SaaS - Development Gameplan

**INTERNAL DOCUMENT - For Development Team Only - Students will refer to the numbered guides in the guides folder**

This document outlines the complete plan for building the Alex Financial Planner SaaS platform. This is the roadmap for Parts 5-8 of the course.

## Current Status

- Parts 1-5: complete, tested and guides written in guides directory
- We recently updated Parts 1-6 to use a new approach for Terraform: storing state locally instead of on S3, and having a separate directory for each guide for its terraform
- Part 6: coded but there are issues that need to be fixed
- We need to resolve the issues with Part 6

## Explaining the issue with Part 6

- The planner was repeatedly failing with strange errors
- You (Claude Code) determined that it seems that tools + structured outputs were not supported at the same time and result in a failure
- We need to make a plan to rebuild Part 6 without using Structured Outputs
- Right now, the planner directory is in a mess with partial code and test code
- Our Action Plan for moving forwards is documented in guides/actionplan.md

ADDITIONAL NOTE:

The BEDROCK_MODEL_ID is in the .env as my preferred model: anthropic.claude-3-7-sonnet-20250219-v1:0
Which I have approved for us-west-2
And I have in .env
BEDROCK_REGION=us-west-2
The actual model name needed to be passed in to LiteLLM is:
bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0
in order to use the right inference profile.
We experienced rate limiting errors with claude 4 - watch out for rate limit errors. If we hit them again, we may need to fall back to using Amazon Nova models (which do not use the us prefix.)

## IMPORTANT - Methodical debugging with the root cause in mind

When you hit bugs, do NOT guess the solution. Do NOT quickly write a workaround. ALWAYS think about the root cause. ALWAYS prove the root cause.

Approach:

1. When hitting a bug, BE AWARE that you have a tendency to jump to conclusions. Don't!
2. BE THOUGHTFUL - identify the root cause, not the immediate problem.
3. Follow a methodical process: Reproduce the problem, prove the problem, consider the bigger picture, determine the root cause, fix it properly - avoid bandaids like exception handlers, isinstance checks and other hacks.
4. Do not prematurely declare victory. Prove that the issue is fully fixed.

## Infrastructure Management Strategy (Terraform)

### Why Separate Terraform Directories?
For this educational project, we use a unique approach designed to simplify the learning experience:
- **Each guide has its own Terraform directory** (e.g., `terraform/2_sagemaker`, `terraform/3_ingestion`)
- **Local state files** instead of remote S3 state (automatically gitignored)
- **Independent deployments** - each part can be deployed without affecting others
- **No state bucket complexity** - eliminates setup and management overhead
- **Progressive deployment** - students can't accidentally deploy later parts

## Package Management Strategy (uv)

### Project Structure
- Each folder within `backend/` is a separate uv project with its own `pyproject.toml`
- This enables independent Lambda packaging and service-specific dependencies
- The `backend/database/` package is shared across all services as an editable dependency
- The top level `backend/` is also a uv project in order to have the utility `deploy_all_lambdas.py`

### Setup Process for Each Project
```bash
cd backend/[service_name]
uv init --bare              # Create minimal pyproject.toml without repo or main.py
uv python pin 3.12          # Pin to Python 3.12 for consistency
uv add --editable ../database  # Add shared database package (for services that need it)
```

### Cross-Platform Approach
- **Always use Python scripts** instead of shell/PowerShell scripts
- Scripts are called with `uv run script_name.py` (works on Mac/Linux/Windows)
- Examples: `package_docker.py` for Lambda packaging using docker so that AWS architecture is supported, `deploy.py` for deployments, `migrate.py` for database migrations
- This ensures consistent behavior across all operating systems

### Benefits
- Clean dependency isolation per service
- Simplified Lambda packaging (each service packages only its dependencies)
- Consistent database models via shared package
- Cross-platform compatibility without maintaining multiple script versions

## Current State (Parts 1-5 Complete)

### Existing Infrastructure
- ✅ SageMaker Serverless endpoint (embeddings)
- ✅ S3 Vectors for knowledge storage
- ✅ Lambda ingest pipeline
- ✅ App Runner researcher service
- ✅ EventBridge scheduler (optional)
- ✅ API Gateway with API key auth

## Database Architecture Summary

### Core Tables (5 total)
1. **users** - Minimal table linking to Clerk auth (display_name, retirement goals, allocation targets)
2. **instruments** - Reference data for ETFs/stocks (symbol, name, type, current price, allocation breakdowns)
3. **accounts** - User investment accounts (401k, IRA, etc.) with cash balances
4. **positions** - Holdings in each account (symbol, quantity, supports fractional shares)
5. **jobs** - Async job tracking for analysis requests (status, results, errors)

### Key Design Decisions
- **Aurora Serverless v2 PostgreSQL with Data API** - No VPC needed, HTTP-based access
- **JSONB for flexible data** - Allocation percentages, job payloads, chart data
- **Pydantic validation** - All data validated before DB insertion, allocations sum to 100%
- **Clerk handles auth** - We only store clerk_user_id as foreign key
- **UUID primary keys** - For accounts, positions, jobs using uuid_generate_v4()
- **Automatic timestamps** - Triggers update updated_at columns

### Pydantic Schema Highlights
- **Literal types for constraints** - RegionType, AssetClassType, SectorType, InstrumentType, JobType
- **Automatic validation** - All allocations validated to sum to 100% with 0.01 tolerance
- **LLM-compatible** - Field descriptions and examples for structured outputs
- **Separate Create/Update schemas** - InstrumentCreate, JobUpdate, etc. for different operations
- **Analysis output schemas** - PortfolioAnalysis, RebalanceRecommendation for agent responses

## Technical Architecture

### AI Models
- **Claude 4 Haiku** via AWS Bedrock for all agents (complex financial analysis)
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
│   ├── 2_sagemaker/         # Part 2: SageMaker endpoint
│   ├── 3_ingestion/         # Part 3: S3 Vectors & Lambda
│   ├── 4_researcher/        # Part 4: App Runner service
│   ├── 5_database/          # Part 5: Aurora Serverless
│   ├── 6_agents/            # Part 6: Agent Lambdas
│   ├── 7_frontend/          # Part 7: API & Frontend infra
│   └── 8_observability/     # Part 8: Monitoring setup
│
├── backend/
│   ├── database/            # Shared library (Guide 5) - uv project
│   │   ├── pyproject.toml
│   │   ├── migrations/
│   │   ├── src/
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

This code shows idiomatic use of OpenAI Agents SDK with appropriate parameters and use of Tools. This is the approach to be used. Only use Tools where they make sense. We will not use Structured Outputs due to Bedrock limitations.

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
    return result.final_output
```

## Part 5: Database & Shared Infrastructure (DONE)

### Objective
Set up Aurora Serverless v2 PostgreSQL with Data API and create a reusable database library that all agents can use.

### Deliverables
- Working Aurora database with Data API
- Shared database package using Data API client
- Database reset script with defaults
- Populated instruments table (20+ ETFs)
- Test data for development

### Acceptance Criteria for Part 5

#### Infrastructure
- [x] Aurora Serverless v2 cluster is running with Data API enabled
- [x] Database credentials stored in Secrets Manager
- [x] Data API endpoint accessible via AWS CLI
- [x] No VPC or networking configuration required

#### Database Schema
- [x] All tables created successfully (users, instruments, accounts, positions, jobs)
- [x] Foreign key constraints working properly
- [x] JSONB columns functioning for flexible data

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
  aws rds-data execute-statement --resource-arn $AURORA_CLUSTER_ARN --secret-arn $AURORA_SECRET_ARN --database alex --sql "SELECT COUNT(*) FROM instruments"
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

---

## Part 6: Agent Orchestra - Core Services (BUILT AND BEING TESTED)

### Objective
Build the AI agent ecosystem where a main orchestrator delegates to specialized agents.

### Steps

1. **Build Financial Planner Agent** (Orchestrator - Lambda)
   - Lambda function with SQS trigger
   - 15 minute timeout, 3GB memory
   - Configurable Bedrock model via `BEDROCK_MODEL_ID` env var
   - Automatically tags missing instruments via Python code (not agent tool)
   - Delegates to other agents via Lambda invocations
   - Has S3 Vectors access for market knowledge
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
                             ├→ [Python: Auto-tag missing instruments]
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

**Simplification Note**: InstrumentTagger is still a Lambda function but is now called automatically by Python code before the agent runs, removing this decision from the agent's workflow. This makes the agent's task simpler and more reliable. This is the ONE task that is OK to use Structured Outputs, as it doesn't use any tools.

### Deliverables
- Working orchestrator Lambda with SQS trigger
- Four specialized Lambda agents (InstrumentTagger, Report Writer, Chart Maker, Retirement)
- Automatic instrument data population
- Full portfolio analysis capability
- Async job processing via SQS

### Testing strategy for Part 6

Prerequisites:

  1. Make sure you're in the project root directory
  2. Ensure your AWS credentials are configured
  3. Have the .env file configured with your settings

### Running the Full Integration Test:

Navigate to the planner directory  
`cd backend/planner`

Run the full test using   
`uv run run_full_test.py`

What the Test Does:

1. Creates a test job in the Aurora database for the test user
2. Submits the job to the SQS queue (alex-analysis-jobs)
3. Triggers the Planner Lambda which orchestrates all agents:
    - InstrumentTagger (classifies unknown instruments)
    - Report Writer (generates analysis narrative)
    - Chart Maker (creates visualization data)
    - Retirement Specialist (projects future outcomes)
4. Monitors progress by polling the database status
5. Shows results when complete (typically 90-120 seconds)

Other Useful Test Commands:

Test the planner locally (without Lambda)  
`uv run test_local.py`

Test just the SQS integration
`uv run test_integration.py`

Check job status in the database
`uv run check_jobs.py`

Test individual agents
`cd ../tagger && uv run test_local.py`
`cd ../reporter && uv run test_local.py`

Monitoring:

- CloudWatch Logs: Check /aws/lambda/alex-planner and other agent logs
- SQS Console: Monitor the alex-analysis-jobs queue
- Database: Use check_jobs.py to see job statuses

Configuration:

The test uses Claude 3.5 Haiku by default. To change models, update .env file: BEDROCK_MODEL_ID and BEDROCK_MODEL_REGION

### Acceptance Criteria for Part 6

#### Lambda Infrastructure
- [ ] All 5 Lambda functions deployed (Planner, Tagger, Reporter, Charter, Retirement)
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

#### Tagger Agent
- [ ] Identifies instruments missing allocation data
- [ ] Successfully calls Bedrock Claude model
- [ ] Returns structured JSON with allocations
- [ ] All percentages sum to 100
- [ ] Updates database with new data

#### Report Writer Agent  
- [ ] Generates markdown analysis report
- [ ] Includes portfolio summary and recommendations
- [ ] Properly formatted for frontend display
- [ ] Saves analysis results to jobs table

#### Chart Maker Agent
- [ ] Calculates portfolio allocations correctly
- [ ] Returns JSON formatted for Recharts
- [ ] Includes asset class, region, and sector breakdowns
- [ ] All chart data percentages sum to 100

#### Retirement Specialist Agent
- [ ] Projects retirement income based on portfolio
- [ ] Generates projection chart data
- [ ] Considers years until retirement
- [ ] Saves projections to jobs table results

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
aws rds-data execute-statement --resource-arn $AURORA_CLUSTER_ARN --secret-arn $AURORA_SECRET_ARN --database alex --sql "SELECT 1"

# Reset database to clean state (drops, migrates, seeds)
cd backend/database
uv run reset_db.py

# Or with test data
uv run reset_db.py --with-test-data

# Or just reload data without dropping
uv run reset_db.py --skip-drop

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
aws cloudwatch get-metric-statistics --namespace "Alex/Agents" --metric-name "InvocationCount" --start-time 2024-01-01T00:00:00Z --end-time 2024-01-02T00:00:00Z --period 3600 --statistics Sum

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

## Lambda Deployment Technique for Binary Compatibility

### The Architecture Issue
Lambda runs on Amazon Linux 2 (x86_64 architecture). When packaging Python dependencies on macOS (ARM64) or Windows, binary packages like `pydantic_core` are compiled for the wrong architecture, causing runtime failures with errors like:
- `ImportError: cannot import name 'ValidationError' from 'pydantic_core'`
- Binary incompatibility errors for packages with C extensions

### Solution: Docker-Based Packaging
Use Docker with the official AWS Lambda Python runtime image to compile dependencies for the correct architecture. This ensures all binary packages are compatible with Lambda's runtime environment.

### Implementation Reference
See `backend/tagger/package_docker.py` for the complete implementation. Key aspects:

1. **Use Official Lambda Runtime Image**:
   ```python
   "public.ecr.aws/lambda/python:3.12"
   ```

2. **Force x86_64 Architecture**:
   ```python
   "--platform", "linux/amd64"
   ```

3. **Install with Binary Compatibility**:
   ```python
   "--platform manylinux2014_x86_64 --only-binary=:all:"
   ```

4. **Cross-Platform Script**:
   - Python script works on Mac/Linux/Windows
   - Called via `uv run package_docker.py`
   - No shell scripts needed

### Usage Pattern
```bash
cd backend/[service_name]
uv run package_docker.py          # Create deployment package
uv run package_docker.py --deploy  # Create and deploy to Lambda
```

This technique is essential for any Lambda deployment with compiled dependencies and should be used for all agent Lambda functions in this project.

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

### Job Tracking
The `jobs` table (already in schema) tracks async operations with status updates and results.

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