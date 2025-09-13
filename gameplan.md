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

### Objective
Build a pure client-side NextJS React app with Clerk authentication, deployed as a static site to S3/CloudFront, calling API Gateway directly.

### Steps

0. Review everything and make a detailed plan (in this document) for how we will approach this, replacing steps 1-7 below with the fleshed out versions that are complete and detailed and cover everything. Do not replace this section.
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

1. Foundations
  1a. Create a NextJS app in the frontend folder. Use TS, use Pages Router, do not have a separate src directory, ensure a static output will be possible, use Tailwind, use latest versions of everything (September 2025). No SSR/ISR - pure client-side
  1b. Create a simple landing page to give the users name, and 1-2 fields from the database for the user
  1c. Create a FastAPI app (uv) in backend/api with some routes related to the user
  1d. Set up the Clerk details based on the SaaS app from week1
  1e. Make any updates to the pages; set up the necessary frontend / api / db hookup so that signing in users are added to the db with the right id
  1f. Be able to deploy and see this locally

2. Deploy
  2a. Make the terraform directory, and put the skeleton terraform for the api backend and static site frontend with cloudfront distribution; handle CORS, preflight, etc
  2b. make the lambda deploy uv script
  2c. Anything else needed around JWT and use of the user_id so that we have row-level security?
  2d. Deploy and test the frontend and backend with the basic dashboard screen
   
3. Build out dashboard to show accounts (frontend + backend including deployment)
   - Add main nav: Dashboard / Account details / Advisor Team / Financial Analysis
   - Add a disclaimer to every single page in the footer that highlights appropriate legal disclaimer (along the lines: this advice has not been vetted by a qualified financial consultant and should not be used for trading decisions, but concisely and in a way that ensures no liability!)
   - Script to populate the database for a given user_id
   - Update dashboard so that you can set name, retirement years, any other high level data, with an update button
   - Update dashboard to show account summary - just names of accounts and some summary details in a nicely formatted table

4. Account details screen with position/instrument entry (frontend + backend including deployment)

5. Advisor Team screen - see a list of prior financial analysis, the ability to switch to view the financial analysis, the ability to kick off a new financial analysis, and the progress of an analysis if it's happening.
Allow the user to click to kick off a run, which puts it on SQS and then polls to show updates of what's going on in a really cool way that gives the strong impression that mutliple Agents are working on the case; this shows when the analysis is complete. This needs to have real wow factor - this is the moment students see it come together! When it's complete, the screen should flip immediately to the Analysis screen

6. Analysis screen - show the results from the reporter, the retirement, and of course.. the Charts!! The reports should appear in full markdown formatted glory. See the implementation in SaaS - we spend ages getting this to look ok - we needed to set the h1/h2/etc styles because Tailwind removes them by default.

7. Finishing up and bulletproofing - iterate on look and feel; add favicon and titles; add error handling; other little things that make it polished; any stuff to ensure JWT security and everything is protected. Finally, make guide 7 for the students!

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