# Alex Financial Planner SaaS - Development Gameplan

**INTERNAL DOCUMENT - For you (Claude Code) and me (the user, Ed) only - Students will refer to the numbered guides in the guides folder**

The Alex project will be deployed by students on the course AI in Production. The code and Terraform scripts are being built by you and me now.

This document covers our plan for building the Alex Financial Planner SaaS platform.

## Current Status

- Parts 1-6: complete and guides written in guides directory
- Part 7 Step 1: ✅ COMPLETE - Landing page, Clerk auth, dashboard, API backend all working. User sync tested successfully.
- Part 7 Step 2: ✅ COMPLETE - Terraform infrastructure, deployment scripts, Lambda packaging all ready. CORS properly configured.

ADDITIONAL NOTE:

The BEDROCK_MODEL_ID is in the .env as my preferred model:
BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0 when local, amazon.nova-pro-v1:0 on lambda
BEDROCK_REGION=us-west-2 local us-east-1 on lambda

The Nova model (us.amazon.nova-pro-v1:0) required special handling:
- Local environment: Uses cross-region inference profile with us. prefix
- Lambda environment: Uses direct model ID amazon.nova-pro-v1:0 with bedrock_region set to us-east-1
- This was due to LiteLLM handling the model ID differently in Lambda vs local environments

## VERY IMPORTANT - debugging process

When you hit bugs, do NOT guess the solution. Do NOT quickly write a workaround. ALWAYS think about the root cause and prove it first.

1. You often jump to conclusions. Don't!
2. BE THOUGHTFUL - identify the root cause, not the immediate problem.
3. Follow a methodical process: Reproduce, prove the problem, consider the bigger picture, determine the root cause, fix properly - avoid bandaids like exception handlers, isinstance checks and other hacks.
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

## IMPORTANT - Agent design

We use OpenAI Agents SDK.
Each Agent has a directory under backend, with a uv project, lambda function, agent.py, templates.py.

The correct package to install is `openai-agents`  
`uv add openai-agents`  
`uv add "openai-agents[litellm]"`  

This code shows idiomatic use with appropriate parameters and use of Tools. Only use Tools where they make sense. We will not use Tools and Structured Outputs together due to Bedrock limitations.
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
- Database reset script with defaults
- Populated instruments table (20+ ETFs)
- Test data for development

## Part 6: Agent Orchestra - Core Services (COMPLETE)

### Objective
Build the AI agent ecosystem where a main orchestrator delegates to specialized agents.

### Key Technical Decision
The OpenAI Agents SDK doesn't support using both tools AND structured outputs simultaneously. Solution:
- **All agents use tools only** (except tagger which uses structured outputs only)
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
- Charter agent returns JSON directly without using tools
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
2. **ALWAYS CHECK REFERENCE IMPLEMENTATIONS FIRST** - You failed to review the saas reference and chose a complex JWT authorizer approach when the reference used simple fastapi-clerk-auth. You invented "alex-api" as an audience value without any basis. This behavior MUST stop.
3. **FOCUS ON SIMPLE AND CONSISTENT CODE** - The saas reference worked perfectly with fastapi-clerk-auth. Instead of using it, you chose python-jose manual validation which was unnecessarily complex. ALWAYS prefer proven, simple solutions from working references.
4. **Database Primary Keys**: The users table uses `clerk_user_id` as the primary key, NOT `id`. When updating users, use the database client directly with clerk_user_id. Other tables (accounts, positions) use UUID `id` fields.
5. **API Response Structure**: The GET /api/user endpoint returns `{user: {...}, created: boolean}`, not the user object directly. Frontend must extract the user from response.user. Always check endpoints to make sure you are using them properly.
6. **Number Formatting**: Always use `toLocaleString('en-US')` for displaying currency and large numbers. For input fields handling currency, use type="text" and strip commas before parsing.
7. **Avoid UI Flicker**: Don't set default values in frontend state - start with empty/zero and let database values populate. All defaults should be set in the database during user creation.
8. **CRITICAL CLERK AUTH PATTERN - STOP MAKING THIS ERROR**: The Alex database schema has NO `user.id` field!
   - `users` table: Primary key is `clerk_user_id` (string), NO separate `id` field exists
   - `accounts` table: Stores `clerk_user_id` directly, NOT `user_id`
   - `jobs` table: Stores `clerk_user_id` directly, NOT `user_id`
   - **NEVER write**: `user['id']`, `account['user_id'] != user['id']`, `job['user_id'] != user['id']`
   - **ALWAYS write**: `clerk_user_id`, `account.get('clerk_user_id') != clerk_user_id`, `job.get('clerk_user_id') != clerk_user_id`
   - This is the THIRD time this exact error was made. Before ANY user/account/job authorization check, remember: there is no user['id'], only clerk_user_id!

### Objective
Build a pure client-side NextJS React app with Clerk authentication, deployed as a static site to S3/CloudFront, calling API Gateway directly.

### Steps

- [x] **Step 0: Review and Planning** ✅ COMPLETE
   - The folder reference/ has projects from earlier in the course and would be helpful reference:
     - The saas app in reference/saas is a working app with a NextJS frontend, using Clerk for user_id. Use the same secrets EXACTLY for minimal setup for the student. This project was called "saas" from week1, and they will have a "saas" repo
     - The files day3.md and day3.part2.md were the instructions for when we set up this Clerk approach in week1 and may help explain the setup
     - The file reference/twin_main.tf is the terraform file from our big project in week2 (the "twin") in which we used lambda, a static site on s3, API gateway, CORS settings, CloudFront distribution - very similar to this project
     - The folder twin/scripts contains the mac and PC scripts that we used to deploy and destroy the infrastructure for twin. We used terraform workspaces for dev, test, prod, and for this project we won't do that - only 1 environment. This contains shell scripts, but for this project we will "uv run" python scripts.
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
- [x] Set up proper TypeScript types for API responses

**1b. Create landing page with Clerk integration**
- [x] Copy Clerk environment variables from reference/saas/.env to frontend/.env.local
- [x] Wrap app with ClerkProvider in _app.tsx
- [x] Create index.tsx as public landing page with:
  - [x] Marketing hero section about AI Financial Advisors
  - [x] Sign In / Sign Up buttons using Clerk's SignInButton component
  - [x] Features showcase (autonomous agents, personalized advice, etc.)
- [x] ~~Add middleware.ts to protect routes~~ Use client-side <Protect> component instead (static export limitation)
- [x] After sign-in, redirect to /dashboard
- [x] Create basic dashboard.tsx with user info display

**1c. Create FastAPI backend in backend/api**
- [x] Initialize uv project with pyproject.toml using the documented approach from prior sections
- [x] uv add: fastapi, fastapi-clerk-auth, boto3, uvicorn, mangum (NOW using fastapi-clerk-auth like saas reference)
- [x] Create main.py with routes:
  - [x] GET /api/user - Get/create user profile (THIS IS WHERE USER SYNC HAPPENS)
  - [x] PUT /api/user - Update user settings
  - [x] GET /api/accounts - List user accounts
  - [x] POST /api/accounts - Create account
  - [x] GET /api/accounts/{account_id}/positions - Get positions for account
  - [x] POST /api/positions - Add/update position
  - [x] POST /api/analyze - Trigger analysis (creates job, sends to SQS)
  - [x] GET /api/jobs/{job_id} - Get job status/results
- [x] JWT validation using fastapi-clerk-auth (CORRECTED - initially used complex python-jose, now matches saas)
- [x] Database operations using backend/database package

**1d. User sync implementation in GET /api/user** ✅ COMPLETE
- [x] Extract clerk_user_id from JWT token (NOW using fastapi-clerk-auth like saas)
- [x] Check if user exists in database
- [x] If NOT exists (first-time user):
  - [x] Auto-create with defaults:
    - clerk_user_id from token
    - display_name from token (or "New User")
    - years_until_retirement: 20
    - target_retirement_income: 100000
    - asset_class_targets: {"equity": 70, "fixed_income": 30}
    - region_targets: {"north_america": 50, "international": 50}
  - [x] Return created user
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

**Critical Environment Variable Lessons:**
- **ALWAYS check existing env vars first** - Before adding new variables, check what prior parts already defined (e.g., database uses AURORA_CLUSTER_ARN from Part 5, not a new DATABASE_ARN)
- **Backend variables go in root .env** - All backend services use the single root .env file via `load_dotenv()`, avoiding nested .env files in subdirectories
- **Reuse existing variables** - Part 7 API reuses AURORA_CLUSTER_ARN, AURORA_SECRET_ARN from Part 5 and DEFAULT_AWS_REGION from Part 1
- **AWS_REGION is reserved** - Use DEFAULT_AWS_REGION instead, as AWS_REGION is reserved by AWS SDKs and can cause conflicts
- **Keep .env.example updated** - The .env.example must match the actual .env template exactly to prevent student configuration errors
- **Terraform follows same pattern** - Variables in .tfvars should also reuse existing values and avoid duplication

**1e. Local testing setup & documentation** ✅ COMPLETE & TESTED
- [x] Remove pages/api directory (incompatible with static export)
- [x] Verify no middleware warnings with static export
- [x] Create scripts/run_local.py to start both frontend and backend
- [x] ~~Create `ed_test_step1.md`~~ Tested successfully and removed
- [x] **Successfully tested**:
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
  - **LESSON LEARNED**: Initially tried to add API Gateway JWT authorizer, which was:
    - Unnecessarily complex
    - Not present in the working saas/twin references
    - Led to inventing "alex-api" audience value (completely made up)
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
- [x] Deploy flow:
  1. Package Lambda with Docker
  2. Build NextJS static site
  3. Deploy infrastructure with Terraform
  4. Upload frontend files to S3
  5. Invalidate CloudFront cache
  6. Output CloudFront URL
- [x] Destroy flow: reverse order with confirmation
- [x] **NOTE**: Run from scripts directory: `cd scripts && uv run deploy.py`

**2d. Deployment testing & documentation** ✅ COMPLETE
- [x] Create `ed_test_step2.md` with:
  - Prerequisites (AWS credentials, Docker running, terraform installed)
  - Deployment commands:
    ```bash
    cd scripts && uv run deploy.py
    ```
  - Test checklist:
    1. CloudFront URL is accessible
    2. Sign in works with Clerk
    3. API Gateway routes respond
    4. User creation in RDS works
    5. CloudWatch logs show Lambda execution
  - AWS Console verification steps
  - Rollback instructions if needed

IMPORTANT: ask me to run `uv run deploy.py` rather than yourself, so that I can watch and wait for it to complete. Same for `uv run run_local.py` - it gets messy if you try to run this yourself.
IMPORTANT: keep `uv run run_local.py` working in addition to the deployed version where possible, so we can test locally as well as deployed.

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
- [x] User settings section:
  - Display name (editable)
  - Years until retirement (slider 0-50)
  - Target allocations (pie chart + inputs)
  - Save button → PUT /api/user
- [x] Portfolio summary cards:
  - Total portfolio value
  - Number of accounts
  - Asset allocation overview (mini pie chart)
  - Last analysis date

**3c. Database population script for testing**
- [ ] Add a small button to the Accounts page to 'populate test data'
- [ ] Create an endpoint that this calls which sets up test data:
  - 3 accounts: "401k Long-term", "Roth IRA", "Brokerage Account"
  - ETF positions in 401K: SPY, VTI, BND, QQQ, IWM with varied quantities
  - An interesting mix of other funds in Roth IRA
  - Stock positions in brokerage account: TSLA, AAPL, AMZN, NVDA
  - Realistic allocations across accounts
- [ ] Text-based summary of the Account details on the Accounts page, to be replaced in Step 4
- [ ] Reset Accounts button to delete all accounts associated with a user

**3d. Dashboard testing & documentation**
- [ ] Have the user (Ed) test local and remote and check the data is created

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
- [ ] **Include mention of Swagger docs at http://localhost:8000/docs for API exploration**
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

This will be built out but will include security, monitoring, observability and guardrails.

## Lambda Deployment Technique for Binary Compatibility

### The Architecture Issue
Lambda runs on Amazon Linux 2 (x86_64 architecture). When packaging Python dependencies on macOS (ARM64) or Windows, binary packages like `pydantic_core` are compiled for the wrong architecture, causing runtime failures.

### Solution: Docker-Based Packaging
Use Docker with the official AWS Lambda Python runtime image to compile dependencies for the correct architecture. This ensures all binary packages are compatible with Lambda's runtime environment.

## Claude Code Performance Warnings

### 1. Hardcoding fallback URLs in React code
**What happened:** When facing undefined environment variables, Claude Code added hardcoded URL fallbacks (`process.env.NEXT_PUBLIC_API_URL || 'https://hardcoded-url'`) directly in React components.
**Why this is bad:** Next.js replaces environment variables at BUILD time not runtime, so the fallback never executes; hardcoding URLs breaks environment separation and requires code changes for different deployments.
**Claude Code's commitment going forwards:** Always solve environment variable issues at the build/deployment configuration level, never hardcode URLs in application code, and recognize that build-time vs runtime resolution is fundamental to Next.js architecture. Most importantly: do not apply bandaids - consider the root cause.
