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
    instrument_type VARCHAR(50),            -- 'equity', 'etf', 'mutual_fund', 'bond_fund'
    
    -- Allocation percentages (0-100)
    allocation_regions JSONB,               -- {"north_america": 60, "europe": 20, "asia": 20}
    allocation_sectors JSONB,               -- {"technology": 30, "healthcare": 20, ...}
    allocation_asset_class JSONB,           -- {"equity": 80, "fixed_income": 20}
    
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
- **RDS PostgreSQL Serverless v2** - Scales to zero, handles Lambda cold starts
- **Lambda** for ALL backend services (agents and API)
- **API Gateway** for REST API endpoints
- **SQS** for async job queue
- **CloudFront + S3** for NextJS static site
- **Clerk** for authentication (no custom auth code)
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
├── frontend/              # NextJS app (Guide 7)
│   ├── app/
│   ├── components/
│   └── lib/
│
└── guides/
    ├── 5_database.md
    ├── 6_agents.md
    ├── 7_frontend.md
    └── 8_observability.md
```

## Part 5: Database & Shared Infrastructure

### Objective
Set up RDS PostgreSQL Serverless v2 and create a reusable database library that all agents can use.

### Steps

1. **Deploy RDS Serverless v2 with Terraform**
   - Create RDS instance in VPC
   - Configure security groups for Lambda access
   - Store credentials in Secrets Manager
   - Output connection string
   - ✅ **Test**: Connect with psql from local machine through bastion or VPN

2. **Create Database Schema**
   - Write SQL migration files (001_schema.sql)
   - Create migration runner script
   - Run migrations against RDS
   - ✅ **Test**: Verify all tables exist with correct structure

3. **Build Shared Database Package** (`backend/database/`)
   - Create uv project with SQLAlchemy models
   - Implement connection pooling for Lambda
   - Create database tools for agents
   - Write unit tests
   - ✅ **Test**: Run pytest suite locally

4. **Seed Instruments Table**
   - Create seed data with popular ETFs (SPY, QQQ, BND, etc.)
   - Include allocation breakdowns
   - ✅ **Test**: Query instruments, verify allocations sum to 100

5. **Create Test Data Loader**
   - Script to create test user with sample portfolio
   - Multiple accounts (401k, IRA, Taxable)
   - Various positions
   - ✅ **Test**: Load data, query full portfolio

### Deliverables
- Working RDS database
- Shared database package
- Populated instruments table
- Test data for development

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

## Part 7: Frontend & Authentication

### Objective
Build a modern NextJS frontend with Clerk authentication, deployed to CloudFront, with Lambda-based API backend.

### Steps

1. **Deploy API Lambda**
   - Lambda function with API Gateway trigger
   - FastAPI or simple request routing
   - JWT validation for Clerk tokens
   - Database operations for portfolios
   - Trigger analysis jobs via SQS
   - ✅ **Test**: API endpoints work via curl/Postman

2. **Set Up Clerk**
   - Create Clerk application
   - Configure OAuth providers (Google, GitHub)
   - Set up webhook Lambda for user sync to RDS
   - Configure JWT for API calls
   - ✅ **Test**: Complete sign-up/sign-in flow

3. **Build NextJS Application Structure**
   - Create app with TypeScript
   - Set up routing (app directory)
   - Configure Clerk middleware
   - Create layouts
   - ✅ **Test**: Dev server runs, routing works

4. **Connect Frontend to API**
   - Configure API Gateway endpoint
   - Handle Clerk JWT in requests
   - CRUD for portfolios
   - Trigger and poll agent analysis
   - ✅ **Test**: Full flow works end-to-end

5. **Build UI Components**
   - Portfolio input forms
   - Position management
   - Chart components (Recharts)
   - Report viewer (markdown)
   - ✅ **Test**: Components render, forms submit

6. **Deploy to S3/CloudFront**
   - Build static export
   - Upload to S3
   - Configure CloudFront distribution
   - Set up custom domain (optional)
   - ✅ **Test**: Production URL works, auth flows work

### Frontend Pages
- `/` - Landing page
- `/dashboard` - User dashboard
- `/portfolio` - Portfolio management
- `/reports` - View analysis reports
- `/settings` - User preferences

### Deliverables
- API Lambda with API Gateway endpoints
- Clerk webhook Lambda for user sync
- Working NextJS app with auth
- Deployed to CloudFront
- Full CRUD for portfolios
- Agent analysis triggering

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
   - VPC endpoints for S3, Bedrock
   - Secrets rotation
   - WAF rules for CloudFront
   - Least privilege IAM
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
- [ ] VPC endpoints configured
- [ ] API rate limiting enabled
- [ ] WAF rules active
- [ ] IAM roles follow least privilege
- [ ] Database encrypted
- [ ] S3 buckets private
- [ ] CloudTrail enabled

### Deliverables
- Full observability in LangFuse
- CloudWatch dashboards
- Security hardening complete
- Cost tracking operational

## Testing Strategy

### Local Testing at Each Stage

**Guide 5 - Database**
```bash
# Test RDS connection
psql $DATABASE_URL -c "SELECT 1"

# Test migrations
cd backend/database
uv run migrations/migrate.py

# Test database package
uv run pytest tests/

# Load and verify test data
uv run scripts/load_sample_data.py
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
# Complete auth flow

# Test API proxy
curl http://localhost:3000/api/portfolio \
  -H "Authorization: Bearer $CLERK_TOKEN"

# Test production build
npm run build
npm run start

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
- [ ] RDS accessible from Lambda/App Runner
- [ ] All tables created with correct schema
- [ ] Database package installable in other services
- [ ] Test data loads successfully

### Part 6 Success
- [ ] Orchestrator delegates to all agents
- [ ] InstrumentTagger populates missing instrument data
- [ ] Each agent produces expected output
- [ ] Full analysis stored in database
- [ ] Charts render correctly in frontend

### Part 7 Success
- [ ] Users can sign up/in via Clerk
- [ ] Portfolio CRUD operations work
- [ ] Agent analysis can be triggered
- [ ] Reports display correctly

### Part 8 Success
- [ ] All agent calls traced in LangFuse
- [ ] CloudWatch dashboards show metrics
- [ ] Security scan passes
- [ ] Costs tracked per user

## Risk Mitigation

### Technical Risks
1. **Lambda cold starts** → Use provisioned concurrency for critical paths
2. **Database connection limits** → Use RDS Proxy if needed
3. **Bedrock throttling** → Implement exponential backoff
4. **Large portfolios** → Pagination and async processing

### Cost Risks
1. **Bedrock usage** → Set per-user limits
2. **RDS always running** → Use Aurora Serverless v2 min capacity 0.5
3. **CloudFront transfer** → Use caching aggressively
4. **LangFuse storage** → Rotate old traces

### Security Risks
1. **API abuse** → Rate limiting and WAF
2. **Data leakage** → Row-level security in database
3. **Token theft** → Short JWT expiry, refresh tokens
4. **SQL injection** → Use parameterized queries only

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

1. **RDS over DynamoDB** - Need relational queries for portfolio analysis
2. **Clerk over Cognito** - Simpler for students, better DX
3. **CloudFront over Amplify** - More control, standard pattern
4. **LangFuse over CloudWatch** - Better agent-specific observability
5. **Claude 4 Sonnet over OSS** - Superior financial analysis quality
6. **Lambda for orchestrator** - 15 min timeout is sufficient, simpler than App Runner
7. **Shared database package** - DRY principle, consistent data access
8. **InstrumentTagger agent** - Auto-populate reference data, reduce manual entry

## Notes for Implementation

### For Ed (Implementation)
- Create database package first - all agents depend on it
- Each backend folder is a separate uv project with its own pyproject.toml
- Database package installed as local dependency: `uv add --editable ../database`
- Integration tests live in backend/planner/tests/ to avoid dependency issues
- Test Lambda packaging carefully with local dependencies
- Ensure Terraform modules are incremental
- Add cost estimates to each guide
- Include troubleshooting sections
- Make Bedrock model configurable via environment variable in all agents
- Default to Claude 4 Sonnet but allow easy switching

### For Students (Guides)
- Each guide should be completable independently
- Include architecture diagrams
- Provide sample data for testing
- Clear success criteria at each step
- Troubleshooting section at the end

## Decisions Made

1. **RDS Proxy**: Not needed for MVP - keep it simple
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