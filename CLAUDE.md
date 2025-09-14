# Alex Financial Planner SaaS - Development Gameplan

8 part project to build Alex, the Agentic AI Financial Planner, to be used in a course on deploying AI.
Students will follow the guides in the guides folder to deploy this.

Parts 1-6 are complete; Part 7 is in progress.

## VERY IMPORTANT - debugging process

When you hit bugs, do NOT guess the solution. Do NOT quickly write a workaround. ALWAYS consider the root cause and prove it.

1. You often jump to conclusions. Don't!
2. BE THOUGHTFUL - identify the root cause.
3. Follow a methodical process: Reproduce, prove the problem, determine the root cause, fix properly - avoid bandaids like exception handlers, isinstance checks and other hacks.
4. Do not declare victory unless you have evidence.
5. Do not be dismissive of issues and call them "expected". Pay attention to every error!

## Infrastructure Management Strategy (Terraform)

### Why Separate Terraform Directories?
For this educational project:
- **Each guide has its own Terraform directory** (e.g., `terraform/2_sagemaker`, `terraform/3_ingestion`)
- **Local state files** instead of remote S3 state
- **Independent deployments** - each part can be deployed without affecting others

## Package Management Strategy (uv)

### Project Structure
- Each folder within `backend/` is a separate uv project with its own `pyproject.toml`
- This enables independent Lambda packaging and service-specific dependencies
- The `backend/database/` package is shared across all services as an editable dependency
- The top level `backend/` is also a uv project for utility scripts
- So is `scripts/` for deployment scripts (Part 7)

### Setup Process for Each Project
```bash
cd backend/[service_name]
uv init --bare              # Create minimal pyproject.toml without repo or main.py
uv python pin 3.12          # Pin to Python 3.12 for consistency
uv add --editable ../database  # Add shared database package (for services that need it)
```

### Cross-Platform Approach
- **Always use Python scripts via uv** instead of shell/PowerShell scripts
- IMPORTANT: Scripts are called with `uv run script_name.py` (works on Mac/Linux/Windows) not `uv python run script_name.py`
- Examples: `package_docker.py` for Lambda packaging using docker so that AWS architecture is supported, `deploy.py` for deployments, `migrate.py` for database migrations

## Current State (Parts 1-6 Complete)

### Parts 1-5

This is a data ingest pipeline that is distinct from Part 6 on. It involves Researcher and Ingest with SageMarker Serverless, S3 Vectors, Lambda, App Runner, EventBridge scheduler, API Gateway with API key auth.

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
│   ├── tagger/             # Instrument tagger (Guide 6) - uv project
│   ├── reporter/           # Report agent (Guide 6) - uv project
│   ├── charter/            # Chart agent (Guide 6) - uv project
│   ├── retirement/         # Retirement agent (Guide 6) - uv project
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

## IMPORTANT - Agent design

We use OpenAI Agents SDK.
Each Agent has a directory under backend, with a uv project, lambda function, agent.py, templates.py.

Correct packages:
`uv add openai-agents`  
`uv add "openai-agents[litellm]"`  

This code shows idiomatic use with Tools. Only use Tools where they make sense. We will not use Tools and Structured Outputs together due to Bedrock limitations.
Use OpenAI Agents SDK correctly. DO NOT invent arguments like passing in additional parameters to trace().

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

## Part 5: Database & Shared Infrastructure (COMPLETE)

### Objective
Set up Aurora Serverless v2 PostgreSQL with Data API and create a reusable database library that all agents can use.

### Deliverables
- Working Aurora database with Data API
- Shared database package using Data API client
- Populated instruments table (20+ ETFs)

## Part 6: Agent Orchestra - Core Services (COMPLETE)

### Objective
Build the AI agent ecosystem where a main orchestrator delegates to specialized agents.

### Key Technical Decision
The OpenAI Agents SDK doesn't support using both tools AND structured outputs simultaneously. Solution:
- **All agents use tools only** (except tagger which uses structured outputs only)
- **Charter agent simplified** - Returns JSON directly without tools
- **Model changed** - From OpenAI OSS to Amazon Nova Pro (us.amazon.nova-pro-v1:0) for better reliability

### Bedrock usage:

Locally
BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0 (cross region inference) BEDROCK_REGION=us-west-2

On Lambda:
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0 when local (direct model ID), BEDROCK_REGION=us-east-1

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

2. **Build tagger Agent** (Lambda)
   - Simple agent for populating missing instrument reference data
   - Uses Structured Outputs to classify instruments
   - Populates: asset_class, regions, sectors allocations
   - Called by orchestrator when instruments lack data
   - Future enhancement: Add Polygon API tool for real-time data

3. **Build reporter Agent** (Lambda)
   - Analyzes portfolio data
   - Generates markdown reports
   - Stores in database

4. **Build charter Agent** (Lambda)
   - Creates JSON data for charts
   - Calculates allocations by asset class, region, sector, with autonomy to decide
   - Formats for Recharts

5. **Build retirment Agent** (Lambda)
   - Projects retirement income
   - Monte Carlo simulations
   - Creates projection charts
   - ✅ **Test**: Calculate projections for test user

6. **Integration Testing**
   - Orchestrator calls all agents including InstrumentTagger
   - Complete portfolio analysis flow

**Deployment Steps** (for user to complete):
- [ ] **Package and deploy all agents**:
  ```bash
  cd /Users/ed/projects/alex/backend
  uv run deploy_all_lambdas.py --package
  ```
- [ ] **Test with real analysis** to verify prices are updated before agents run

**Benefits**:
- Charter agent now calculates accurate portfolio values
- All analysis based on current market prices
- Single efficient API call to Yahoo Finance
- Graceful fallback for any symbols that fail

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

**Implementation Notes**: 
- Tagger called with code before the agent runs (not as tool)
- Tagger is the ONLY agent that uses Structured Outputs (no tools needed)
- Charter agent returns JSON directly without using tools
- All other agents use tools with RunContextWrapper pattern for clean access to job_id

### Testing Strategy for Part 6

Each agent has the following in their directory:
- `test_simple.py` - Local testing with mock data
- `test_full.py` - Remote testing with deployed Lambda

The backend directory has:
- `test_simple.py` - Tests all agents locally
- `test_full.py` - Tests via SQS/Lambda
- `test_multiple_accounts.py` - Tests multi-account scenarios
- `test_scale.py` - Tests concurrent processing for 5 users

All tests confirmed working with Nova Pro model.

## Part 7: Frontend & Authentication ✅ COMPLETE

### Context & Decisions Made
This section implements the user-facing frontend for the Alex Financial Advisor platform. Key architectural decisions:
- **Authentication**: Using Clerk with the EXACT same credentials from week1 SaaS project (students already have these)
- **Frontend**: NextJS with Pages Router (not App Router due to Clerk compatibility), static export for S3/CloudFront
- **Backend**: Single Lambda function with FastAPI handling all API routes, JWT validation via Clerk
- **User Sync**: Auto-create users on first sign-in with sensible defaults (20 years to retirement, 70/30 equity/fixed income)
- **Agent Display**: Show 4 visible agents (Planner, Reporter, Charter, Retirement) - Tagger runs invisibly
- **Testing**: Comprehensive test documents (ed_test_*.md) at each milestone for coordination
- **Styling**: Enterprise look with edgy AI accents (primary #209DD7, AI/agent #753991, accent #FFB707, dark #062147)

### NextJS 15 & Tailwind CSS 4 - Critical Changes (September 2025)
**NextJS 15 Breaking Changes:**
- **No default caching**: GET Route Handlers and Client Router Cache are now uncached by default
- **Async APIs**: cookies(), headers(), and params now require `await`
- **ESLint 9**: New flat config format (eslint.config.mjs instead of .eslintrc)
- **Removed APIs**: geo and ip properties removed from NextRequest
- **Static Export Limitations**: With `output: 'export'`:
  - NO middleware.ts support
  - NO API routes (pages/api)
  - All auth must be client-side

**Tailwind CSS 4 Revolutionary Changes:**
- **NO tailwind.config.js/ts file**: Configuration now lives in CSS via @theme directive
- **Single import**: Just `@import "tailwindcss"` in globals.css - no more @tailwind directives
- **CSS-first configuration**: Custom colors/themes defined in CSS with @theme block
- **PostCSS plugin**: Uses `@tailwindcss/postcss` instead of traditional config
- **Performance**: 5x faster full builds, 100x faster incremental builds
- **New color format**: OKLCH recommended for better color manipulation

**Key Implementation Notes:**
- Custom colors go in @theme block with --color- prefix (e.g., --color-primary: #209DD7)
- No Sass/SCSS compatibility - pure CSS only
- Size utilities changed: use `size-10` instead of `w-10 h-10`
- Dark mode via CSS variables and media queries, not config file

**Critical Discovery - Static Export & Authentication:**
- Must use Clerk's `<Protect>` component for client-side route protection
- No middleware.ts allowed with static export
- Pattern: Wrap protected content in `<Protect fallback={<Loading />}>` 
- All API calls must go to external backend (Lambda/API Gateway)

## Frontend Style Guidelines for Consistency

### Design System Established in Step 1
The landing page and dashboard have established excellent patterns that should be maintained throughout:

**Layout Structure:**
- Min-height screens with bg-gray-50 or gradient backgrounds
- White content cards with shadow and rounded-lg
- Consistent padding: px-4 sm:px-6 lg:px-8 for responsive containers
- max-w-7xl mx-auto for content width
- Navigation: white bg with shadow-sm border-b, h-16 height

**Typography Hierarchy:**
- Brand: "Alex" in dark + "AI Financial Advisor" in primary color
- Page titles: text-2xl to text-5xl font-bold text-dark
- Section headers: text-xl to text-2xl font-semibold
- Body text: text-gray-600
- Small/meta text: text-sm text-gray-500

**Color Usage:**
- Primary actions: bg-primary hover:bg-blue-600
- AI/Agent features: bg-ai-accent hover:bg-purple-700
- Success states: text-green-600
- Error states: text-red-500
- Info boxes: bg-ai-accent/10 border-ai-accent/20
- Subtle backgrounds: bg-gray-50

**Component Patterns:**
- Buttons: px-6 py-2 (standard) or px-8 py-4 (large), rounded-lg, transition-colors
- Cards: bg-white rounded-lg shadow p-6
- Info panels: colored bg with /10 opacity, matching border with /20 opacity
- Status messages: Inline colored text with icons (✅, 🎯, etc.)

**Interactive Elements:**
- Hover states with transition-colors
- Modal-based auth (SignInButton/SignUpButton with mode="modal")
- Loading states: "Syncing..." text patterns
- Error handling: Inline error messages in red

**VERY IMPORTANT - You MUST follow these crucial rules**
1. During your ongoing work, you MUST use absolute paths when changing directories. The project root on this machine is at `/Users/ed/projects/alex` and if you try relative directory changes you often make mistakes. ALWAYS use absolute paths when you `cd` to be reliable.
2. You MUST pay attention to uv. Never use python directly. Always `uv run my_module.py` NEVER `uv run python xx` and NEVER `python xx`. If you want to run python code directly, the format is `uv run python -c 'print("hello")'`. Installing a package is `uv add xx` not `uv pip install xx`.
3. NEVER guess arguments because you are ALWAYS wrong. For example, you tried to create a User in the database and invented parameters. Always check the code!

**Lessons learned**
1. CORS Configuration Pattern: API Gateway uses `allow_origins = ["*"]` and `allow_credentials = false`. Lambda handles auth, not API Gateway.
2. **Database Primary Keys**: The users table uses `clerk_user_id` as the primary key, NOT `id`. When updating users, use the database client directly with clerk_user_id. Other tables (accounts, positions) use UUID `id` fields.
3. **API Response Structure**: The GET /api/user endpoint returns `{user: {...}, created: boolean}`, not the user object directly. Frontend must extract the user from response.user. Always check endpoints to make sure you are using them properly.
4. **Number Formatting**: Always use `toLocaleString('en-US')` for displaying currency and large numbers. For input fields handling currency, use type="text" and strip commas before parsing.

### Objective
Build a pure client-side NextJS React app with Clerk authentication, deployed as a static site to S3/CloudFront, calling API Gateway directly.

### Steps

- [x] **Step 0: Review and Planning** ✅ COMPLETE
   - The folder reference/ has projects from earlier in the course and would be helpful reference:
     - The saas app in reference/saas is a working app with a NextJS frontend, using Clerk
     - The files day3.md and day3.part2.md were instructions for when we set up this saas app
     - The file reference/twin_main.tf is from our big project in week2 called twin in which we used lambda, a static site on s3, API gateway, CORS settings, CloudFront distribution
   - Color scheme (and all shades of these)
     - primary color (boring): #209DD7 
     - primary color (anything to do with AI or Agents, like kicking off the planner): #753991
     - accent color (anything bright or exciting): #FFB707
     - dark color: #062147
     - And usual red and green variations for good and bad things
     - Look and feel should be relatively "enterprise" since this is all about Production Deployment, but with an edgy, exciting feel to it given this is autonomous agents. Light mode.

### Step 1: Foundations
**1a. Create NextJS app with Pages Router**
- [x] Initialize NextJS in `frontend/` using Pages Router (not App Router) with TypeScript
- [x] Configure for static export with `output: 'export'` in next.config.ts
- [x] Use Tailwind CSS with custom color scheme (primary #209DD7, AI/agent #753991, accent #FFB707, dark #062147)
- [x] Install dependencies: @clerk/nextjs, react-markdown, remark-gfm, remark-breaks, recharts, @microsoft/fetch-event-source
- [x] TypeScript types

**1b. Create landing page with Clerk integration**
- [x] Copy Clerk environment variables
- [x] Wrap app with ClerkProvider in _app.tsx
- [x] Create index.tsx as public landing page
- [x] ~~Add middleware.ts to protect routes~~ Use client-side <Protect> component instead (static export limitation)
- [x] After sign-in, redirect to /dashboard
- [x] Create basic dashboard.tsx

**1c. Create FastAPI backend in backend/api** ✅ COMPLETE
- [x] Initialize uv project
- [x] uv add: fastapi, fastapi-clerk-auth, boto3, uvicorn, mangum
- [x] Create main.py with routes:
  - [x] GET /api/user - Get/create user profile
  - [x] PUT /api/user - Update user settings
  - [x] GET /api/accounts - List user accounts
  - [x] POST /api/accounts - Create account
  - [x] GET /api/accounts/{account_id}/positions - Get positions for account
  - [x] POST /api/positions - Add/update position
  - [x] POST /api/analyze - Trigger analysis (creates job, sends to SQS)
  - [x] GET /api/jobs/{job_id} - Get job status/results
- [x] JWT validation using fastapi-clerk-auth
- [x] Database operations using backend/database package

**1d. User sync implementation in GET /api/user** ✅ COMPLETE
- [x] Extract clerk_user_id from JWT token (NOW using fastapi-clerk-auth like saas)
- [x] Check if user exists in database
- [x] If NOT exists (first-time user) - auto-create with defaults and return it
- [x] If exists: return existing user data
- [x] Frontend calls this on every dashboard load to ensure user exists

**Important Backend Notes for Next Steps:**
- **Database Import Pattern**: Import as `from src import Database` not `from alex_database`
- **Database Usage**: Use `db = Database()` then access via `db.users`, `db.accounts`, `db.positions`, `db.jobs`
- **Clerk Authentication**: Use fastapi-clerk-auth EXACTLY like saas reference:
  ```python
  clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
  clerk_guard = ClerkHTTPBearer(clerk_config)
  ```
  NO API Gateway JWT authorizer, NO manual JWT validation
- **Missing Schemas**: Created UserUpdate, AccountUpdate, PositionUpdate as Pydantic models in API
- **Database Methods**:
  - Users: `db.users.find_by_clerk_id(clerk_user_id)`, `db.users.create_user(...)`
  - Accounts: `db.accounts.find_by_user(clerk_user_id)`, `db.accounts.create_account(...)`
  - Positions: `db.positions.find_by_account(account_id)`, `db.positions.add_position(...)`
  - Jobs: `db.jobs.create_job(...)`, `db.jobs.update_status(...)`
- **Lambda Packaging**: Use package_docker.py for binary compatibility


**1e. Local testing setup & documentation** ✅ COMPLETE & TESTED
- [x] Remove pages/api directory (incompatible with static export)
- [x] Verify no middleware warnings with static export
- [x] Create scripts/run_local.py to start both frontend and backend
- [x] ~~Create `ed_test_step1.md`~~ Tested successfully and removed
- [x] **Successfully tested**

### Step 2: Deploy Infrastructure ✅ COMPLETE
**2a. Terraform configuration in terraform/7_frontend/**
- [x] Create main.tf with:
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
- [x] CORS configuration:
  - **IMPORTANT**: API Gateway uses `allow_origins = ["*"]` with `allow_credentials = false`
  - NO JWT authorizer at API Gateway level (auth handled in Lambda)
  - **LESSON LEARNED**: Initially tried to add API Gateway JWT authorizer, which was complex and bad
  - **CORRECT APPROACH**: Use fastapi-clerk-auth in Lambda exactly like saas reference
- [x] Environment variables for Lambda from existing infrastructure

**2b. Lambda packaging script (backend/api/package_docker.py)** ✅ COMPLETE
- [x] Uses Docker with AWS Lambda Python 3.12 image
- [x] Installs dependencies for correct architecture
- [x] Packages FastAPI app as Lambda handler using mangum
- [x] Creates api_lambda.zip with all dependencies
- [x] Fixed database package path issue (uses src/ not alex_database/)

**2c. Deployment scripts (scripts/deploy.py, scripts/destroy.py)** ✅ COMPLETE
- [x] Python scripts using subprocess to run terraform/aws/npm commands
- [x] Deploy flow
- [x] Destroy flow: reverse order with confirmation
- [x] **NOTE**: Run from scripts directory: `cd scripts && uv run deploy.py`

### Step 3: Dashboard with Account Management
**3a. Navigation and layout components**
- [x] Create components/Layout.tsx with nav bar:
  - Logo/brand: "Alex AI Financial Advisor"
  - Navigation: Dashboard | Accounts | Advisor Team | Analysis
  - User button (Clerk) in top right
- [x] Footer with disclaimer: "This AI-generated advice has not been vetted by a qualified financial advisor and should not be used for trading decisions. For informational purposes only."

**3b. Dashboard page (pages/dashboard.tsx)**
- [x] On page load:
  - Call GET /api/user (this auto-creates user if first time)
  - Load user data and accounts
- [x] User settings section
- [x] Portfolio summary cards

**3c. Database population script for testing**
- [x] Add a small button to the Accounts page to 'populate test data'
- [x] Create an endpoint that this calls which sets up test data
- [x] Text-based summary of the Account details on the Accounts page, to be replaced in Step 4
- [x] Reset Accounts button to delete all accounts associated with a user

**3d. Dashboard testing & documentation**
- [x] Have the user (Ed) test local and remote and check the data is created

### Step 4: Account Details Page
**4a. Accounts list page (pages/accounts.tsx)**
- [x] Table showing all accounts
- [x] Add account
- [x] Remove account

**4b. Account detail/edit page (pages/accounts/[id].tsx)**
- [x] Account information (editable):
  - Name, purpose, cash balance
- [x] Positions table:
  - Symbol, name, quantity, current price, total value
  - Inline edit for quantities
  - Delete position button
- [x] Add position form:
  - Symbol autocomplete (from instruments table)
  - Or enter new instrument not in instruments table (created automatically by backend)
  - Quantity input
  - Add button → POST /api/positions

### Step 5: Advisor Team & Analysis Trigger
**5a. Advisor Team page (pages/advisor-team.tsx)**
- [x] Agent cards in grid layout (4 visible agents)
- [x] Note: Market Researcher (tagger) runs invisibly in background when needed
- [x] Previous analyses list
- [x] "Start New Analysis" button (prominent, purple #753991)

**5b. Analysis progress visualization**
- [x] After clicking "Start New Analysis":
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
- [x] If job fails: show error panel with details
- [x] Retry button to trigger new analysis
- [x] Show last successful analysis if available

### Step 6: Analysis Results Page ✅ COMPLETE
**6a. Analysis page structure (pages/analysis.tsx)**
- [x] Load from job results (markdown + JSON)
- [x] Hero section with completion timestamp
- [x] Tabbed interface

**6b. Markdown rendering with styling**
- [x] Use ReactMarkdown with remark-gfm and remark-breaks
- [x] Custom CSS for financial reports

**6c. Interactive charts using Recharts**
- [x] Render charter agent's JSON output

**6d. Real-Time Market Data Integration**

**Objective**: Update the Planner to fetch real-time stock prices using yfinance after the tagger runs, ensuring all agents work with current market data.

**6e. CHANGE IN PLAN FOR MARKET DATA - switch to polygon.io**
- yfinance is too unstable and the dependencies are too large. Different approach is needed
- see reference implementation in backend/planner/market_new.py
- [x] Implement polygon.io alternative

### Step 7: Polish & Production Readiness - ✅ COMPLETE
**7a. UI/UX refinements**
- [x] Loading states with skeletons
- [x] Smooth transitions between pages
- [x] Toast notifications for actions
- [x] Responsive design for mobile
- [x] Favicon and page titles
- [x] 404 and error pages

**7b. Security hardening**
- [x] JWT expiry handling → redirect to sign-in
- [x] API rate limiting (100 req/min) via API Gateway
- [x] Input validation on all forms
- [x] XSS protection via Content Security Policy
- [x] Secrets in AWS Secrets Manager (not env vars)

**7c. Error handling & monitoring**
- [x] Global error boundary in React
- [x] API error responses with user-friendly messages
- [x] Do an `npm run build` and fix any build errors

**8. Guide 7 documentation**
- [x] Write guide 7

## Docker image must be built for x86_64

When packaging Python dependencies, binary packages like `pydantic_core` are compiled for the wrong architecture, causing runtime failures.
Solution: Use Docker with the official AWS Lambda Python runtime image.

## Critical API Architecture Understanding

### API URL Configuration (FINAL APPROACH)
**Frontend uses `lib/config.ts` for all API calls:**
```javascript
// All pages import: import { API_URL } from "../lib/config"
// Then use: fetch(`${API_URL}/api/endpoint`)
```

**How it works:**
- **Local development**: Detects `localhost` → returns `http://localhost:8000`
- **Production**: Returns empty string → uses relative paths (CloudFront routes `/api/*` to API Gateway)
- **No environment variables needed** in frontend for API URL

### Authentication Pattern
**All API calls require JWT token from Clerk:**
```javascript
const { getToken } = useAuth();
const token = await getToken();
const response = await fetch(`${API_URL}/api/endpoint`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### Deployment Process (deploy.py)
1. **Package Lambda**: `cd backend/api && uv run package_docker.py`
2. **Deploy Infrastructure**: Terraform creates API Gateway, Lambda, S3, CloudFront
3. **Build Frontend**: NextJS static export (uses `lib/config.ts`, no env vars needed)
4. **Upload to S3**: Static files served via CloudFront
5. **Result**: CloudFront serves frontend and proxies `/api/*` to API Gateway

## Part 8: Enterprise Grade: Scalability, Security, APIs, Monitoring, Guardrails & Observability (NOT STARTED)

### Objective
Implement comprehensive observability with LangFuse, monitoring with CloudWatch, and security best practices.
We may not need to terraform directory at all for this part - it might just be a guide, and some code changes activated by adding an env variable

### Section 1: 
- [ ] Start guide 8_enterprise.md to cover topics related to making our project enterprise strength
- [ ] Write Section 1: Scalability. Explain to the student that the serverless architecture is already prepared to scale up. Show them the settings in terraform where we could ramp up our infrastructure if we wanted to

## Section 2:
- [ ] Write Section 2: Security. Point the student to the aspects of the Alex project that have security best practices:
  - Our IAM controls, for example controlling what the Agents can do
  - The API key for the API
  - The JWT controls
  - API gateway throttling etc
  - CORS controls
  - The XSS controls
  - Point out other enterprise strength controls that we could add through tf configuration if we wished

### Section 3: Add more on monitoring
- [ ] First, check how much logging the agents do, and as necessary add more logging. Also ensure the API logs users logging in/out, kicking off runs, etc
- [ ] Write Section 3: monitoring. Show how to build a dashboard from CloudWatch to see what is happening with our API and agents; log in, do a run, see everything in the logs
- [ ] In Section 3, include any other AWS features (like SQS dashboard)

### Section 4: Guardrails
- [ ] Write Section 4: Guardrails. Give the student some code that they could add to Charter to validate that the output is well formed json, and if not, to refuse to write the charts and log an issue. (Don't actually make this code change in the repo; let the student do it themselves)

### Section 5: Explainability
- [ ] Write Section 5: Explainability. First, introduce the topic of Explainability. Make the case that this was a serious concern in the early days of Deep Learning (black box deep neural networks), but in many ways modern LLMs and Agentic systems help address the issue of explainable AI with Generative AI that explains its reasoning.
- [ ] As an example, show the students how they can edit the structured outputs coming from the Tagger agent to include its rationale for why it gave the breakdowns it did. This rationale wouldn't get returned to the planner agent, but instead log it. Be sure that the rationale is the first field in the structured output, so the LLM needs to generate the rationale BEFORE it generates the answer. Don't make this code change in the repo; just tell the students how to do it.

### Section 6: Observability with LangFuse THIS IS THE NEXT STEP TO DO!

#### Research Findings - LangFuse + OpenAI Agents SDK Integration

**References:**
- Official LangFuse Documentation: https://langfuse.com/integrations/frameworks/openai-agents
- OpenAI Agents SDK Docs: https://openai.github.io/openai-agents-python/
- Strategic Analysis (July 2025): https://thinhdanggroup.github.io/agent-observability/

##### How the Integration Actually Works

LangFuse does NOT directly integrate with OpenAI Agents SDK. Instead, it uses a chain of technologies:

```
OpenAI Agents SDK → Pydantic Logfire (instrumentation) → OpenTelemetry → LangFuse
```

**Key Discovery:** There is NO `openai-agents[langfuse]` package extra. The integration requires separate packages:

```bash
# Required packages (corrected - pydantic-ai now includes logfire by default)
pip install openai-agents langfuse pydantic-ai
# Or with uv:
uv add openai-agents langfuse pydantic-ai
```

##### Implementation Pattern

```python
import os
import logfire
from langfuse import get_client
from agents import Agent, Runner, trace

# Configure Logfire to send traces to LangFuse (not Logfire cloud)
logfire.configure(
    service_name='alex_financial_advisor',
    send_to_logfire=False  # Critical: Don't send to Logfire cloud
)

# Instrument OpenAI Agents SDK
logfire.instrument_openai_agents()

# Initialize LangFuse client
langfuse = get_client()
langfuse.auth_check()  # Verify connection

# Now your agents are instrumented
agent = Agent(name="Assistant", instructions="You are a helpful assistant")
result = await Runner.run(agent, "What is the meaning of life?")
```

##### What Gets Traced
- Agent planning and execution phases
- Function tool calls with arguments and results
- Multi-agent handoffs and delegation
- Token usage and estimated costs
- Latency metrics per step
- Errors with full Python tracebacks
- Correlation IDs for distributed tracing

##### Lambda-Specific Considerations

**Challenges:**
1. **Cold Start Overhead**: OpenTelemetry + Logfire + LangFuse adds ~200-500ms initialization
2. **Background Processing**: LangFuse optimized for background trace sending (problematic in Lambda's stateless environment)
3. **Trace Flushing**: Lambda may terminate before traces are sent to LangFuse

**Solutions:**
- Ensure proper flushing before Lambda returns
- Consider Lambda SnapStart or Provisioned Concurrency for production
- Use environment variables for configuration (no config files)

#### Implementation Gameplan

##### Step 1: Ed Sets Up LangFuse Account
- [ ] Go to https://cloud.langfuse.com and create free account
- [ ] Create organization (required first step):
  - Organization name: Your name or company
  - Organization type: Personal organization
  - Members: Just yourself
- [ ] Create new project called "alex-financial-advisor"
- [ ] Navigate to Settings → API Keys
- [ ] Create new API keys and save:
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_HOST` (usually https://cloud.langfuse.com)

##### Step 2: Add to Local .env
- [ ] Add to `/Users/ed/projects/alex/.env`:
```bash
# LangFuse Observability (optional)
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

##### Step 3: Create Test Script
- [ ] Create `backend/test_langfuse.py`:
```python
import os
import asyncio
from dotenv import load_dotenv
import logfire
from langfuse import get_client
from agents import Agent, Runner, trace, function_tool

load_dotenv(override=True)

@function_tool
async def get_meaning() -> str:
    """Get the meaning of life from the universe"""
    return "42"

async def test_langfuse_integration():
    # Only proceed if LangFuse env vars are set
    if not os.getenv("LANGFUSE_SECRET_KEY"):
        print("❌ LangFuse not configured - skipping observability")
        return

    print("🔧 Configuring Logfire...")
    logfire.configure(
        service_name='alex_test',
        send_to_logfire=False
    )

    print("📡 Instrumenting OpenAI Agents SDK...")
    logfire.instrument_openai_agents()

    print("✅ Connecting to LangFuse...")
    langfuse = get_client()
    langfuse.auth_check()

    print("🤖 Creating test agent...")
    with trace("Test Meaning of Life"):
        agent = Agent(
            name="Philosopher",
            instructions="You are a wise philosopher. Use the get_meaning tool to find the meaning of life.",
            model="gpt-4o-mini",
            tools=[get_meaning]
        )

        result = await Runner.run(
            agent,
            "What is the meaning of life?",
            max_turns=3
        )

        print(f"📝 Result: {result.messages[-1].content}")

    print("✨ Check LangFuse dashboard for traces!")
    print(f"🔗 {os.getenv('LANGFUSE_HOST')}")

if __name__ == "__main__":
    asyncio.run(test_langfuse_integration())
```

- [ ] Install dependencies: `uv add openai-agents langfuse pydantic-ai`
- [ ] Run test: `uv run test_langfuse.py`
- [ ] Verify traces appear in LangFuse dashboard

##### Step 4: Add to Tagger Agent (Proof of Concept)
- [ ] Update `backend/tagger/pyproject.toml` dependencies
- [ ] Modify `backend/tagger/agent.py`:
```python
import os
import logfire
from langfuse import get_client

def setup_observability():
    """Set up LangFuse observability if configured"""
    if os.getenv("LANGFUSE_SECRET_KEY"):
        logfire.configure(
            service_name='alex_tagger_agent',
            send_to_logfire=False
        )
        logfire.instrument_openai_agents()
        langfuse = get_client()
        langfuse.auth_check()
        return True
    return False

async def tag_instrument(symbol: str, name: str, instrument_type: str) -> InstrumentAllocation:
    """Tag an instrument with allocations"""
    observability_enabled = setup_observability()

    # Rest of existing code...
    with trace("Tag Instrument" if observability_enabled else None):
        # Existing agent code
```

##### Step 5: Add to Terraform
- [ ] Update `terraform/6_agents/variables.tf`:
```hcl
variable "langfuse_public_key" {
  description = "LangFuse public key for observability"
  type        = string
  default     = ""
  sensitive   = false
}

variable "langfuse_secret_key" {
  description = "LangFuse secret key for observability"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_host" {
  description = "LangFuse host URL"
  type        = string
  default     = "https://cloud.langfuse.com"
}
```

- [ ] Update Lambda environment variables in `terraform/6_agents/main.tf` for tagger:
```hcl
environment {
  variables = {
    # Existing vars...
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key
    LANGFUSE_HOST       = var.langfuse_host
  }
}
```

##### Step 6: Deploy and Test on Lambda
- [ ] Package tagger: `cd backend/tagger && uv run package_docker.py`
- [ ] Deploy with terraform:
```bash
cd terraform/6_agents
terraform apply -var="langfuse_public_key=$LANGFUSE_PUBLIC_KEY" \
                -var="langfuse_secret_key=$LANGFUSE_SECRET_KEY"
```
- [ ] Trigger tagger Lambda via test event or from planner
- [ ] Check LangFuse dashboard for Lambda traces
- [ ] Monitor cold start impact and trace completeness

##### Step 7: Roll Out to Other Agents (If Successful)
- [ ] If tagger works well, apply same pattern to:
  - [ ] Planner (most complex, do last)
  - [ ] Reporter
  - [ ] Charter
  - [ ] Retirement
- [ ] Each agent should only initialize LangFuse if env vars present
- [ ] This allows code to be in repo without requiring LangFuse

#### Important Notes
- The integration is optional - agents work without LangFuse configured
- No `openai-agents[langfuse]` extra exists - install packages separately
- Logfire is the instrumentation layer, not a direct integration
- Test locally first, then Lambda with ONE agent before rolling out

### Finale
- [ ] End with a paragraph to congratulate them on the deployment of an enterprise grade agentic ai system!
- [ ] Summarise with a bullet each: this system is scalable, secure, robust/monitored, has guardrails, is explainable and observable. Mission accomplished!