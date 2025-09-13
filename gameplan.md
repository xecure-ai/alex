# Alex Financial Planner SaaS - Development Gameplan

**INTERNAL DOCUMENT - For you (Claude Code) and me (the user, Ed) only - Students will refer to the numbered guides in the guides folder**

The Alex project will be deployed by students on the course AI in Production. The code and Terraform scripts are being built by you and me now.

This document covers our plan for building the Alex Financial Planner SaaS platform.

## Current Status

- Parts 1-5: complete, tested and guides written in guides directory
- New approach for Terraform implemented: storing state locally instead of on S3, and having a separate terraform subdirectory for each guide
- Part 6: coded, being tested

## Explaining the issue with Part 6

- The planner was repeatedly failing with strange errors
- Root cause: tools + structured outputs are not supported at the same time with Bedrock
- We made a plan to rebuild Part 6 without using Structured Outputs, documented in guides/actionplan.md and in progress

ADDITIONAL NOTE:

The BEDROCK_MODEL_ID is in the .env as my preferred model:
BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0 CHANGED to us.amazon.nova-pro-v1:0 for stability
BEDROCK_REGION=us-west-2 locally us-east-1 in deployment

The Nova model (us.amazon.nova-pro-v1:0) required special handling:
- Local environment: Uses cross-region inference profile with us. prefix
- Lambda environment: Uses direct model ID amazon.nova-pro-v1:0 with bedrock_region set to us-east-1
- This was due to LiteLLM handling the model ID differently in Lambda vs local environments

## IMPORTANT - Methodical debugging with the root cause in mind

When you hit bugs, do NOT guess the solution. Do NOT quickly write a workaround. ALWAYS think about the root cause. ALWAYS prove the root cause.

Approach:

1. When hitting a bug, BE AWARE that you have a tendency to jump to conclusions. Don't!
2. BE THOUGHTFUL - identify the root cause, not the immediate problem.
3. Follow a methodical process: Reproduce the problem, prove the problem, consider the bigger picture, determine the root cause, fix properly - avoid bandaids like exception handlers, isinstance checks and other hacks.
4. Do not prematurely declare victory. Prove that the issue is fully fixed.
5. Beware: you have a tendancy to be dismissive of issues and call them "expected". Pay attention to every error!

## Infrastructure Management Strategy (Terraform)

### Why Separate Terraform Directories?
For this educational project, we use a simple approach:
- **Each guide has its own Terraform directory** (e.g., `terraform/2_sagemaker`, `terraform/3_ingestion`)
- **Local state files** instead of remote S3 state
- **Independent deployments** - each part can be deployed without affecting others

## Package Management Strategy (uv)

### Project Structure
- Each folder within `backend/` is a separate uv project with its own `pyproject.toml`
- This enables independent Lambda packaging and service-specific dependencies
- The `backend/database/` package is shared across all services as an editable dependency
- The top level `backend/` is also a uv project for utility scripts

### Setup Process for Each Project
```bash
cd backend/[service_name]
uv init --bare              # Create minimal pyproject.toml without repo or main.py
uv python pin 3.12          # Pin to Python 3.12 for consistency
uv add --editable ../database  # Add shared database package (for services that need it)
```

### Cross-Platform Approach
- **Always use Python scripts** instead of shell/PowerShell scripts
- IMPORTANT: Scripts are called with `uv run script_name.py` (works on Mac/Linux/Windows) not `uv python run script_name.py`
- Examples: `package_docker.py` for Lambda packaging using docker so that AWS architecture is supported, `deploy.py` for deployments, `migrate.py` for database migrations
- This ensures consistent behavior across all operating systems

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
│   │
│   ├── tagger/             # Instrument tagger (Guide 6) - uv project
│   │
│   ├── reporter/           # Report agent (Guide 6) - uv project
│   │
│   ├── charter/            # Chart agent (Guide 6) - uv project
│   │
│   ├── retirement/         # Retirement agent (Guide 6) - uv project
│   │
│   └── api/               # Backend API (Guide 7) - uv project
│
├── frontend/              # NextJS React SPA (Guide 7)
│
└── guides/
    ├── 5_database.md
    ├── 6_agents.md
    ├── 7_frontend.md
    └── 8_observability.md
```

## IMPORTANT - Read this - Agent design

For Agents, we will be using OpenAI Agents SDK.
Each Agent is in its own directory under backend, with its own uv project, lambda function, agent.py, templates.py.

The correct package to install is `openai-agents`  
`uv add openai-agents`  
`uv add "openai-agents[litellm]"`  

This code shows idiomatic use with appropriate parameters and use of Tools. Only use Tools where they make sense. We will not use Tools and Structured Outputs together due to Bedrock limitations.
BE CAREFUL to consult up to date docs on OpenAI Agents SDK. DO NOT invent arguments like passing in additional parameters to trace().

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

## Part 6: Agent Orchestra - Core Services (COMPLETE)

### Objective
Build the AI agent ecosystem where a main orchestrator delegates to specialized agents.

### Key Technical Decision
The OpenAI Agents SDK doesn't support using both tools AND structured outputs simultaneously. Solution:
- **All agents use tools only** (except InstrumentTagger which uses structured outputs only)
- **Charter agent simplified** - Returns JSON directly without tools
- **Model changed** - From OpenAI OSS to Amazon Nova Pro (us.amazon.nova-pro-v1:0) for better reliability

### Agent structure

Every agent folder has the following:

pyproject.toml # uv details  
lambda_handler.py # the lambda function
agent.py # the agent and tool code
templates.py # the instructions and task templates
package_docker.py # to package up
xxx_lambda.zip # the zip
test_simple.py # the local test
test_full.py # the remote test

### Steps

1. **Build planner agent** (planner - Lambda)
   - Lambda function with SQS trigger
   - 15 minute timeout, 3GB memory
   - Configurable Bedrock model via `BEDROCK_MODEL_ID` env var
   - Automatically tags missing instruments via Python code (not agent tool)
   - Delegates to other agents via Lambda invocations
   - Has S3 Vectors access for market knowledge
   - Updates job status in database at end
   - ✅ **Test**: Local invocation, SQS message processing

2. **Build tagger Agent** (Lambda)
   - Simple agent for populating missing instrument reference data
   - Uses Structured Outputs to classify instruments
   - Populates: asset_class, regions, sectors allocations
   - Called by orchestrator when instruments lack data
   - Future enhancement: Add Polygon API tool for real-time data
   - ✅ **Test**: Tag various ETFs and stocks, verify allocations sum to 100

3. **Build reporter Agent** (Lambda)
   - Analyzes portfolio data
   - Generates markdown reports
   - Stores in database
   - ✅ **Test**: Invoke with test portfolio, verify markdown output

4. **Build charter Agent** (Lambda)
   - Creates JSON data for charts
   - Calculates allocations by asset class, region, sector, with autonomy to decide
   - Formats for Recharts
   - ✅ **Test**: Verify JSON structure matches Recharts schema

5. **Build retirment Agent** (Lambda)
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

**Key Implementation Notes**: 
- Tagger is called automatically by Python code before the agent runs (not as an agent tool)
- Tagger is the ONLY agent that uses Structured Outputs (no tools needed)
- Charter agent returns JSON directly without using tools (simplified from earlier design)
- All other agents use tools with RunContextWrapper pattern for clean access to job_id

### Testing Strategy for Part 6

Each of the 5 agents has the following in their directory:
- `test_simple.py` - Local testing with mock data
- `test_full.py` - Remote testing with deployed Lambda

The backend parent directory has overall test scripts:
- `test_simple.py` - Tests all agents locally
- `test_full.py` - Tests via SQS/Lambda
- `test_multiple_accounts.py` - Tests multi-account scenarios
- `test_scale.py` - Tests concurrent processing for 5 users

All tests confirmed working with Nova Pro model.

## Part 7: Frontend & Authentication

### Context & Decisions Made
This section implements the user-facing frontend for the Alex Financial Advisor platform. Key architectural decisions:
- **Authentication**: Using Clerk with the EXACT same credentials from week1 SaaS project (students already have these)
- **Frontend**: NextJS with Pages Router (not App Router due to Clerk compatibility), static export for S3/CloudFront
- **Backend**: Single Lambda function with FastAPI handling all API routes, JWT validation via Clerk
- **User Sync**: Auto-create users on first sign-in with sensible defaults (20 years to retirement, 70/30 equity/fixed income)
- **Agent Display**: Show 4 visible agents (Planner, Reporter, Charter, Retirement) - Tagger runs invisibly
- **Testing**: Comprehensive test documents (ed_test_*.md) at each milestone for coordination
- **Styling**: Enterprise look with edgy AI accents (primary #209DD7, AI/agent #753991, accent #FFB707, dark #062147)

### Objective
Build a pure client-side NextJS React app with Clerk authentication, deployed as a static site to S3/CloudFront, calling API Gateway directly.

### Steps

- [x] **Step 0: Review and Planning** ✅ COMPLETE
   - Start by looking in the folder reference/ for some projects from earlier in the course (that worked) and would be helpful reference for you:
     - The saas app in reference/saas is a working app with a NextJS frontend like we want, using Clerk for user_id (and subscriptions, which we won't use). If this is OK, I'd like to use the same secrets EXACTLY - like the same secret key and public key - for minimal setup for the student. This project was called "saas" from week1, and they will have a "saas" repo
     - The files day3.md and day3.part2.md were the instructions for when we set up this Clerk approach in week1 and may help explain the setup
     - The file reference/twin_main.tf is the terraform file from our big project in week2 (the "twin") in which we used lambda, a static site on s3, API gateway, CORS settings, CloudFront distribution - very similar to what we will do now
     - The folder twin/scripts contains the mac and PC scripts that we used to deploy and destroy the infrastructure for twin. We used terraform workspaces for dev, test, prod, and for this project we won't do that - only 1 environment. Also we used powershell and shell scripts, but for this project I'd prefer to have python scripts obviously, in a uv project. But you should follow similar patterns.
   - Color scheme (and all shades of these)
     - primary color (boring): #209DD7 
     - primary color (anything to do with AI or Agents, like kicking off the planner): #753991
     - accent color (anything bright or exciting): #FFB707
     - dark color: #062147
     - And usual red and green variations for good and bad things
     - Overall look and feel should be relatively "enterprise" since this is all about Production Deployment, but with an edgy, exciting feel to it given this is autonomous agents.
     - Overall light mode, not dark mode.
   - After reviewing these references, reflect on the task ahead, and flesh out the sections below, adding details and substance to each section. DO NOT PROCEED TO WORK ON THE SECTIONS - just flesh out the instructions

### Step 1: Foundations
**1a. Create NextJS app with Pages Router**
- [ ] Initialize NextJS in `frontend/` using Pages Router (not App Router) with TypeScript
- [ ] Configure for static export with `output: 'export'` in next.config.ts
- [ ] Use Tailwind CSS with custom color scheme (primary #209DD7, AI/agent #753991, accent #FFB707, dark #062147)
- [ ] Install dependencies: @clerk/nextjs, react-markdown, remark-gfm, remark-breaks, recharts, @microsoft/fetch-event-source
- [ ] Set up proper TypeScript types for API responses

**1b. Create landing page with Clerk integration**
- [ ] Copy Clerk environment variables from reference/saas/.env to frontend/.env.local
- [ ] Wrap app with ClerkProvider in _app.tsx
- [ ] Create index.tsx as public landing page with:
  - [ ] Marketing hero section about AI Financial Advisors
  - [ ] Sign In / Sign Up buttons using Clerk's SignInButton component
  - [ ] Features showcase (autonomous agents, personalized advice, etc.)
- [ ] Add middleware.ts to protect routes (dashboard, accounts, etc.) - redirect to sign-in if not authenticated
- [ ] After sign-in, redirect to /dashboard

**1c. Create FastAPI backend in backend/api**
- [ ] Initialize uv project with pyproject.toml
- [ ] Install: fastapi, fastapi-clerk-auth, boto3, uvicorn, mangum (for Lambda)
- [ ] Create main.py with routes:
  - [ ] GET /api/user - Get/create user profile (THIS IS WHERE USER SYNC HAPPENS)
  - [ ] PUT /api/user - Update user settings
  - [ ] GET /api/accounts - List user accounts
  - [ ] POST /api/accounts - Create account
  - [ ] GET /api/positions - Get positions for account
  - [ ] POST /api/positions - Add/update position
  - [ ] POST /api/analyze - Trigger analysis (creates job, sends to SQS)
  - [ ] GET /api/jobs/{job_id} - Get job status/results
- [ ] JWT validation using fastapi-clerk-auth with CLERK_JWKS_URL on ALL routes
- [ ] Database operations using backend/database package

**1d. User sync implementation in GET /api/user**
- [ ] Extract clerk_user_id from JWT token (via fastapi-clerk-auth)
- [ ] Check if user exists in database
- [ ] If NOT exists (first-time user):
  - [ ] Auto-create with defaults:
    - clerk_user_id from token
    - display_name from token (or "New User")
    - years_until_retirement: 20
    - target_retirement_income: 100000
    - asset_class_targets: {"equity": 70, "fixed_income": 30}
    - region_targets: {"north_america": 50, "international": 50}
  - [ ] Return created user
- [ ] If exists: return existing user data
- [ ] Frontend calls this on every dashboard load to ensure user exists

**1e. Local testing setup & documentation**
- [ ] Create scripts/run_local.py to start both frontend and backend
- [ ] Create `ed_test_step1.md` with:
  - Prerequisites checklist (npm installed, database running, .env files in place)
  - Commands to run:
    ```bash
    cd frontend && npm install
    cd ../backend/api && uv sync
    cd ../.. && uv run scripts/run_local.py
    ```
  - Test checklist:
    1. Visit http://localhost:3000 - see landing page
    2. Click Sign In - redirected to Clerk
    3. Sign in with Google/GitHub - redirected to /dashboard
    4. Check browser DevTools Network tab - see GET /api/user call
    5. Check database - confirm user was created with clerk_user_id
    6. Edit user settings - confirm PUT /api/user works
    7. Sign out and sign in again - confirm user is loaded (not recreated)
  - SQL queries to verify:
    ```sql
    SELECT * FROM users WHERE clerk_user_id LIKE '%your-id%';
    ```
  - Troubleshooting common issues (CORS, JWT validation, etc.)
  - Expected outcomes with screenshots placeholders

### Step 2: Deploy Infrastructure
**2a. Terraform configuration in terraform/7_frontend/**
- [ ] Create main.tf with:
  - S3 bucket for static frontend (with website configuration)
  - CloudFront distribution with:
    - S3 origin for frontend
    - API Gateway origin for /api/* paths
    - Custom error pages for SPA routing
  - API Gateway HTTP API with JWT authorizer using Clerk JWKS
  - Lambda function for API backend
  - IAM roles with permissions for:
    - Aurora Data API access
    - SQS send message
    - Lambda invoke (for direct agent testing)
    - Secrets Manager read
- [ ] CORS configuration:
  - Allow origins: CloudFront domain + http://localhost:3000
  - Allow headers: Authorization, Content-Type
  - Handle preflight OPTIONS requests
- [ ] Environment variables for Lambda from existing infrastructure

**2b. Lambda packaging script (scripts/package_api.py)**
- [ ] Use Docker with AWS Lambda Python 3.12 image
- [ ] Install dependencies for correct architecture
- [ ] Package FastAPI app as Lambda handler using mangum
- [ ] Create deployment zip with all dependencies

**2c. Deployment scripts (scripts/deploy.py, scripts/destroy.py)**
- [ ] Python scripts using subprocess to run terraform/aws/npm commands
- [ ] Deploy flow:
  1. Package Lambda with Docker
  2. Build NextJS static site
  3. Deploy infrastructure with Terraform
  4. Upload frontend files to S3
  5. Invalidate CloudFront cache
  6. Output CloudFront URL
- [ ] Destroy flow: reverse order with confirmation

**2d. Deployment testing & documentation**
- [ ] Create `ed_test_step2.md` with:
  - Prerequisites (AWS credentials, Docker running, terraform installed)
  - Deployment commands:
    ```bash
    uv run scripts/deploy.py
    ```
  - Test checklist:
    1. CloudFront URL is accessible
    2. Sign in works with Clerk
    3. API Gateway routes respond
    4. User creation in RDS works
    5. CloudWatch logs show Lambda execution
  - AWS Console verification steps
  - Rollback instructions if needed

### Step 3: Dashboard with Account Management
**3a. Navigation and layout components**
- [ ] Create components/Layout.tsx with nav bar:
  - Logo/brand: "Alex AI Financial Advisor"
  - Navigation: Dashboard | Accounts | Advisor Team | Analysis
  - User button (Clerk) in top right
- [ ] Footer with disclaimer: "This AI-generated advice has not been vetted by a qualified financial advisor and should not be used for trading decisions. For informational purposes only."

**3b. Dashboard page (pages/dashboard.tsx)**
- [ ] On page load:
  - Call GET /api/user (this auto-creates user if first time)
  - Load user data and accounts
- [ ] User settings section:
  - Display name (editable)
  - Years until retirement (slider 0-50)
  - Target allocations (pie chart + inputs)
  - Save button → PUT /api/user
- [ ] Portfolio summary cards:
  - Total portfolio value
  - Number of accounts
  - Asset allocation overview (mini pie chart)
  - Last analysis date

**3c. Database population script (scripts/populate_demo.py)**
- [ ] Creates demo data for a given clerk_user_id:
  - 3 accounts: "401k Vanguard", "Roth IRA Fidelity", "Taxable Brokerage"
  - ETF positions: SPY, VTI, BND, QQQ, IWM with varied quantities
  - Stock positions: TSLA, AAPL, AMZN, NVDA
  - Realistic allocations across accounts

**3d. Dashboard testing & documentation**
- [ ] Create `ed_test_step3.md` with:
  - Setup commands:
    ```bash
    uv run scripts/populate_demo.py --user-id YOUR_CLERK_ID
    uv run scripts/deploy.py  # redeploy with new pages
    ```
  - Test checklist:
    1. Dashboard shows user settings
    2. Portfolio summary cards display correctly
    3. Edit user settings and save
    4. Verify accounts appear from demo data
    5. Navigation between pages works
  - Visual regression checks (layout, colors, responsiveness)

### Step 4: Account Details Page
**4a. Accounts list page (pages/accounts.tsx)**
- [ ] Table showing all accounts:
  - Account name, type, total value
  - Number of positions
  - Cash balance
  - Edit/View buttons
- [ ] "Add Account" button → modal

**4b. Account detail/edit page (pages/accounts/[id].tsx)**
- [ ] Account information (editable):
  - Name, purpose, cash balance
- [ ] Positions table:
  - Symbol, name, quantity, current price, total value
  - Inline edit for quantities
  - Delete position button
- [ ] Add position form:
  - Symbol autocomplete (from instruments table)
  - Quantity input
  - Add button → POST /api/positions

**4c. Real-time price updates**
- [ ] Fetch current prices from database
- [ ] Calculate total values client-side
- [ ] Show allocation breakdowns per account

**4d. Accounts testing & documentation**
- [ ] Create `ed_test_step4.md` with:
  - Test checklist:
    1. View all accounts in list
    2. Click through to account details
    3. Add new position (test symbol autocomplete)
    4. Edit position quantities
    5. Delete a position
    6. Verify calculations are correct
    7. Create new account
  - Database verification queries
  - Edge cases to test (invalid symbols, negative quantities, etc.)

### Step 5: Advisor Team & Analysis Trigger
**5a. Advisor Team page (pages/advisor-team.tsx)**
- [ ] Agent cards in grid layout (4 visible agents):
  - 🎯 Financial Planner (orchestrator) - purple accent - "Coordinates your financial analysis"
  - 📊 Portfolio Analyst (reporter) - blue - "Analyzes your holdings and performance"
  - 📈 Chart Specialist (charter) - green - "Visualizes your portfolio composition"  
  - 🎯 Retirement Planner (retirement) - orange - "Projects your retirement readiness"
- [ ] Note: Market Researcher (tagger) runs invisibly in background when needed
- [ ] Previous analyses list:
  - Job ID, date, status, view button
  - Click to load analysis on Analysis page
- [ ] "Start New Analysis" button (prominent, purple #753991)

**5b. Analysis progress visualization**
- [ ] After clicking "Start New Analysis":
  - Create job → POST /api/analyze
  - Show progress panel with 4 agent avatars
  - Poll /api/jobs/{job_id} every 2 seconds
  - Progress stages:
    1. Financial Planner lights up first: "Coordinating analysis..."
    2. Three agents light up simultaneously: "Agents working in parallel..."
    3. All complete: "Analysis complete!"
  - Show status messages based on job updates
  - Animated pulse/glow effect on active agents
  - Small progress bar or spinner for overall progress
  - Upon completion: auto-navigate to Analysis page

**5c. Error handling**
- [ ] If job fails: show error panel with details
- [ ] Retry button to trigger new analysis
- [ ] Show last successful analysis if available

**5d. Analysis trigger testing & documentation**
- [ ] Create `ed_test_step5.md` with:
  - Prerequisites (ensure agents are deployed from Part 6)
  - Test checklist:
    1. View Advisor Team page with agent cards
    2. Click "Start New Analysis" 
    3. Watch progress visualization (agents lighting up)
    4. Verify SQS message sent
    5. Monitor job progress (2-3 minutes)
    6. Auto-redirect to Analysis page on completion
    7. Test error scenario (if possible)
  - AWS Console checks:
    - SQS messages
    - Lambda invocations
    - CloudWatch logs for each agent
  - Database queries to check job status

### Step 6: Analysis Results Page
**6a. Analysis page structure (pages/analysis.tsx)**
- [ ] Load from job results (markdown + JSON)
- [ ] Hero section with completion timestamp
- [ ] Tabbed interface:
  - Overview (reporter output)
  - Charts (charter output)
  - Retirement Projection (retirement output)
  - Recommendations

**6b. Markdown rendering with styling**
- [ ] Use ReactMarkdown with remark-gfm and remark-breaks
- [ ] Custom CSS for financial reports:
  ```css
  /* Restore heading styles that Tailwind removes */
  .prose h1 { @apply text-3xl font-bold mb-4 text-gray-900; }
  .prose h2 { @apply text-2xl font-semibold mb-3 text-gray-800; }
  .prose h3 { @apply text-xl font-medium mb-2 text-gray-700; }
  .prose ul { @apply list-disc ml-6 mb-4; }
  .prose ol { @apply list-decimal ml-6 mb-4; }
  .prose table { @apply w-full border-collapse mb-4; }
  .prose th { @apply bg-gray-100 p-2 text-left font-semibold; }
  .prose td { @apply border p-2; }
  ```

**6c. Interactive charts using Recharts**
- [ ] Render charter agent's JSON output as:
  - Pie charts for allocations (asset class, region, sector)
  - Bar charts for account comparisons
  - Line charts for retirement projections
- [ ] Color-coded with our palette
- [ ] Hover tooltips with details
- [ ] Responsive sizing

**6d. Analysis results testing & documentation**
- [ ] Create `ed_test_step6.md` with:
  - Test checklist:
    1. View completed analysis
    2. Switch between tabs (Overview, Charts, Retirement)
    3. Verify markdown rendering (headers, lists, tables)
    4. Interact with charts (hover, tooltips)
    5. Check responsive design on mobile view
    6. Print preview looks reasonable
  - Visual checks for professional appearance
  - Performance metrics (page load time)

### Step 7: Polish & Production Readiness
**7a. UI/UX refinements**
- [ ] Loading states with skeletons
- [ ] Smooth transitions between pages
- [ ] Toast notifications for actions
- [ ] Responsive design for mobile
- [ ] Favicon and page titles
- [ ] 404 and error pages

**7b. Performance optimizations**
- [ ] Image optimization (NextJS Image component where applicable)
- [ ] Code splitting
- [ ] Minimize bundle size
- [ ] CloudFront caching headers
- [ ] API response caching where appropriate

**7c. Security hardening**
- [ ] JWT expiry handling → redirect to sign-in
- [ ] API rate limiting (100 req/min) via API Gateway
- [ ] Input validation on all forms
- [ ] XSS protection via Content Security Policy
- [ ] Secrets in AWS Secrets Manager (not env vars)

**7d. Error handling & monitoring**
- [ ] Global error boundary in React
- [ ] API error responses with user-friendly messages
- [ ] Detailed errors in expandable sections
- [ ] CloudWatch logs for Lambda
- [ ] Frontend error tracking (console.error with context)

**7e. Guide 7 documentation**
- [ ] Step-by-step setup instructions
- [ ] Architecture diagram
- [ ] Troubleshooting section
- [ ] Cost considerations
- [ ] Deployment checklist

**7f. Final comprehensive testing & documentation**
- [ ] Create `ed_test_final.md` with:
  - End-to-end test scenario:
    1. Fresh deployment from scratch
    2. New user sign-up flow
    3. Populate demo data
    4. Navigate all pages
    5. Trigger full analysis
    6. View results
    7. Sign out and sign in
  - Performance benchmarks:
    - Page load times
    - API response times
    - Analysis completion time
  - Security checklist:
    - JWT validation working
    - Can't access other users' data
    - API rate limiting active
  - Production readiness checklist
  - Cost monitoring setup verification

## Part 8: Observability, Monitoring & Security (NOT STARTED)

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

## Lambda Deployment Technique for Binary Compatibility

### The Architecture Issue
Lambda runs on Amazon Linux 2 (x86_64 architecture). When packaging Python dependencies on macOS (ARM64) or Windows, binary packages like `pydantic_core` are compiled for the wrong architecture, causing runtime failures with errors like:
- `ImportError: cannot import name 'ValidationError' from 'pydantic_core'`
- Binary incompatibility errors for packages with C extensions

### Solution: Docker-Based Packaging
Use Docker with the official AWS Lambda Python runtime image to compile dependencies for the correct architecture. This ensures all binary packages are compatible with Lambda's runtime environment.

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