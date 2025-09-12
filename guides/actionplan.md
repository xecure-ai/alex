# Action Plan - Part 6 Agent Orchestra Fix

## 📊 Current Status: READY FOR PHASE 6 - INTEGRATION TESTING

### Completed Phases:
- ✅ **Phase 1**: Database Schema Update (COMPLETE)
- ✅ **Phase 2**: Fix Individual Agents (COMPLETE)
- ✅ **Phase 3**: Fix Orchestrator (COMPLETE)  
- ✅ **Phase 4**: Lambda Packaging and Deployment (COMPLETE)
- ✅ **Phase 5**: Terraform Infrastructure (COMPLETE)
- 🔄 **Phase 6**: Integration Testing (READY TO START)
- ⏳ **Phase 7**: Documentation & Cleanup (PENDING)

## Problem Statement

The OpenAI Agents SDK (formerly Swarm) currently doesn't support using both tools AND structured outputs simultaneously in a single agent. When we configure an agent with both:
- `tools=[...]` for calling functions
- `output_type=SomeModel` for structured outputs

The agent fails with errors, making our orchestrator pattern unusable in its current form.

## Crucial - repeated mistakes

You frequently are in the wrong directory when you run commands. DO NOT cd to a relative path because you OFTEN get this wrong. You MUST use absolute paths as you work.
You frequently do "python xxx" instead of "uv run xxx". ALWAYS use uv.
The current date is September 2025.

## Objectives

### Core Requirements
1. **Fix the tools + structured outputs conflict** - Each agent should use either tools OR structured outputs, never both
2. **Maintain agent autonomy** - The planner should decide which specialist agents to call based on context
3. **Enable local testing** - Developers should be able to test the complete flow without deploying to Lambda
4. **Keep it simple** - Clean, readable code that students can understand and learn from

### Design Principles
- **Idiomatic code** - Short methods, clear naming, minimal complexity
- **Minimal error handling** - Only catch what's necessary, let real errors surface
- **Clean test files** - Simple test scenarios that demonstrate functionality
- **Educational value** - The system should clearly demonstrate multi-agent collaboration

Keep comments concise and minimal.
If you need to retry (say to avoid rate limiting) use the tenacity package.
Keep tests clean and simple.

## Architecture Decision

**All agents will use tools only - no structured outputs**

### Important: AWS Region Handling

**Environment Variables for Regions**:

1. **`BEDROCK_REGION`** (e.g., `us-west-2`) - Used for Bedrock/Claude API calls
   - LiteLLM expects the region in `AWS_REGION_NAME` environment variable
   - In each agent, we set: `os.environ['AWS_REGION_NAME'] = os.getenv('BEDROCK_REGION', 'us-west-2')`
   - This ONLY affects LiteLLM's Bedrock calls, not other AWS services

2. **`DEFAULT_AWS_REGION`** (e.g., `us-east-1`) - Used for all other AWS services
   - SageMaker endpoints
   - S3 Vectors
   - Aurora database (though it also extracts region from cluster ARN)
   - Any other AWS service calls

**Implementation Pattern**:
```python
# For Bedrock/LiteLLM calls:
bedrock_region = os.getenv('BEDROCK_REGION', 'us-west-2')
os.environ['AWS_REGION_NAME'] = bedrock_region

# For other AWS services:
default_region = os.getenv('DEFAULT_AWS_REGION', 'us-east-1')
sagemaker = boto3.client('sagemaker-runtime', region_name=default_region)
```

**Key Points**:
- Never set `AWS_REGION` or `AWS_DEFAULT_REGION` as these affect ALL boto3 calls
- Always use `AWS_REGION_NAME` for LiteLLM (it's specific to that library)
- Always pass `region_name` explicitly to boto3 clients for non-Bedrock services

The InstrumentTagger (special case):
- Called directly via Lambda invocation (not as an agent tool)
- Runs as a pre-processing step before the main orchestration
- Already implemented correctly in `handle_missing_instruments()`
- Updates the database with missing instrument allocations

Each specialized agent (Reporter, Charter, Retirement) will:
- Use **tools not structured outputs**
- Charter will also use a tool to write to the database; Reporter and Retirement will return markdown as final output to be saved
- Generate analysis through natural language processing (no structured output models)
- The lambda function returns simple success confirmations to the orchestrator

The orchestrator (Planner) will:
- Pre-process with InstrumentTagger (non-autonomous, always runs if needed)
- Use **tools only** to call other agents and finalize results
- Have autonomy to decide which agents to invoke (Reporter, Charter, Retirement)
- Pass job_id to each agent for database access
- Use a `finalize_job` tool to mark analysis complete

### Important: new simple approach for tools

Problem: several of the tools need access to variables like job_id
Previous bad solution: created the tools as closures with job_id; complex and hard to read
New, simple, idiomatic solution: use RunContextWrapper per this documentation from OpenAI Agents SDK:

```python
from dataclasses import dataclass

from agents import Agent, RunContextWrapper, Runner, function_tool

@dataclass
class UserInfo:  
    name: str
    uid: int

@function_tool
async def fetch_user_age(wrapper: RunContextWrapper[UserInfo]) -> str:  
    """Fetch the age of the user. Call this function to get user's age information."""
    return f"The user {wrapper.context.name} is 47 years old"

async def main():
    user_info = UserInfo(name="John", uid=123)

    agent = Agent[UserInfo](  
        name="Assistant",
        tools=[fetch_user_age],
    )

    result = await Runner.run(  
        starting_agent=agent,
        input="What is the age of the user?",
        context=user_info,
    )

    print(result.final_output)  
    # The user John is 47 years old.
    ```

### Model decision

We have decided to use this model, set as BEDROCK_MODEL_ID in the .env file:
BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0
BEDROCK_REGION=us-west-2
I have access to this in us-west-2, and it reliably calls tools and has high rate limits.

### Database Package Architecture

**How the database package is structured and imported:**

The database package (`backend/database`) is a separate uv project with the following key characteristics:

1. **Package Name**: `alex-database` (defined in `backend/database/pyproject.toml`)
2. **Package Contents**: The `src` directory containing all database code
3. **Installation Method**: Editable install via uv: `alex-database = { path = "../database", editable = true }`

**Import Pattern (IMPORTANT):**

The correct import pattern for ALL agents is:
```python
from src import Database
from src.schemas import InstrumentCreate, JobCreate, etc.
```

Do NOT use:
- `from database.src import Database` ❌
- `from alex-database.src import Database` ❌

**Why this works consistently:**

1. **Local Development (with uv run)**:
   - The editable install adds `/backend/database` to Python's sys.path
   - The `src` directory becomes directly importable as a top-level module
   - Running `uv run test_simple.py` automatically sets up the environment correctly

2. **Lambda Deployment**:
   - The `package_docker.py` script runs: `pip install --target ./package --no-deps /database`
   - This installs the `src` directory directly into the Lambda package
   - In Lambda, `src` is a top-level module in the package directory
   - The same `from src import Database` import works

3. **Docker Packaging Process**:
   - Each agent's `package_docker.py` mounts the database directory: `-v {backend_dir}/database:/database`
   - Installs it into the package: `pip install --target ./package --no-deps /database`
   - This ensures binary compatibility with AWS Lambda's runtime environment

**Key Design Decision**: By packaging only the `src` directory (not the entire database folder), we ensure consistent imports across all environments without needing conditional imports or try/except blocks.

## Implementation Checklist

### Phase 1: Database Schema Update (Improved Design) ✅ COMPLETE
- [x] Update jobs table schema to have separate JSONB fields:
  - Keep `request_payload` (for initial request data)
  - Remove or deprecate `result_payload` (was too generic)
  - Add `report_payload` (Reporter agent's markdown analysis)
  - Add `charts_payload` (Charter agent's visualization data)
  - Add `retirement_payload` (Retirement agent's projections)
  - Add `summary_payload` (Planner's final summary/metadata)
- [x] Update Jobs model with new field methods
- [x] Update migration scripts with new schema
- [x] Test that each agent can write to its own field independently
- [x] No merging needed - each agent writes to its dedicated field

### Phase 2: Fix Individual Agents (Tagger, Reporter, Charter, Retirement)

#### 2.0 InstrumentTagger Agent (Pre-processing, Not Autonomous) ✅ COMPLETE
- [x] Verify current implementation uses structured outputs correctly
- [x] Confirm it's NOT using tools (structured outputs only is fine here)
- [x] Test that `handle_missing_instruments()` in planner works correctly
- [x] Verify database updates happen properly
- [x] Create test_tagger_standalone.py to test classification
- [x] Test with missing instruments: `uv run test_tagger_standalone.py`
- [x] Note: This agent is special - it's called directly, not via agent tools

#### 2.1 Reporter Agent ✅ COMPLETE
- [x] Remove PortfolioReport structured output model
- [x] Add `update_job_report` tool to write to report_payload field
- [x] Add `get_market_insights` tool to retrieve S3 Vectors knowledge
- [x] Modify lambda_handler to:
  - Accept job_id in event
  - Load portfolio from database using job_id
  - Run agent with tools to generate and store report
  - Return simple success response
- [x] Create test_reporter.py with minimal test case
- [x] Test locally with: `uv run test_reporter.py`
- [x] Fixed SAGEMAKER_ENDPOINT environment variable in Terraform config

#### 2.2 Charter Agent ✅ COMPLETE
- [x] Remove PortfolioCharts structured output model
- [x] Add `update_job_charts` tool to write to charts_payload field (simplified to single `create_chart` tool)
- [x] Add `calculate_allocations` tool for data processing (provided in context instead)
- [x] Modify lambda_handler to:
  - Accept job_id in event
  - Accept portfolio_data in event (not loading from database)
  - Run agent with tools to generate and store charts
  - Return simple success response
- [x] Create test_charter.py with minimal test case
- [x] Test locally with: `uv run test_charter.py`
- [x] **Bonus improvements**: Simplified to single tool, portfolio analysis provided in context

#### 2.3 Retirement Agent ✅ COMPLETE
- [x] Remove RetirementAnalysis structured output model
- [x] Add `update_job_retirement` tool to write to retirement_payload field
- [x] Simplified Monte Carlo - runs in background, provided as context (not as tool)
- [x] Modify lambda_handler to:
  - Accept job_id in event
  - Load portfolio from database if not provided
  - Load user preferences from database (not passed separately)
  - Run agent with tools to generate and store projections
  - Return simple success response
- [x] Create test_retirement.py with minimal test case
- [x] Test locally with: `uv run test_retirement.py`
- [x] Fixed database region handling to extract from ARN

### Phase 3: Fix Orchestrator (Planner) ✅ COMPLETE

#### 3.1 Remove Structured Output ✅ COMPLETE
- [x] Remove AnalysisResult model completely
- [x] Update templates.py with clearer autonomy instructions
- [x] Keep agent configuration to tools only

#### 3.2 Simplify Tool Functions ✅ COMPLETE
- [x] Update `invoke_reporter` to pass job_id only
- [x] Update `invoke_charter` to pass job_id and portfolio_data
- [x] Update `invoke_retirement` to pass job_id only
- [x] Remove hardcoded return values
- [x] Add `finalize_job` tool for completion

#### 3.3 Add Local Testing Support ✅ COMPLETE
- [x] Add MOCK_LAMBDAS environment variable check
- [x] Implement local agent calling when MOCK_LAMBDAS=true
- [x] Create test_local.py for isolated testing with mocked agents
- [x] Clean up outdated test files (removed duplicates)
- [x] Fix AWS region handling with environment variables for LiteLLM

#### 3.4 Add Rate Limit Handling ✅ COMPLETE
- [x] Add tenacity dependency for exponential backoff
- [x] Wrap Runner.run with @retry decorator
- [x] Configure retry for RateLimitError with 5 attempts
- [x] Add logging for retry attempts

### Phase 4: Lambda Packaging and Deployment

#### 4.1 Verify Local Testing ✅ COMPLETE
- [x] test_local.py already implemented and tested
- [x] Confirms orchestrator works with mocked agents
- [x] Shows autonomous decision making

#### 4.2 Fix Package Scripts ✅ COMPLETE
- [x] Fixed missing tenacity dependency in planner/package_docker.py
- [x] Fixed missing agent.py file in reporter/package_docker.py  
- [x] Fixed missing database package installation in charter/package_docker.py
- [x] Fixed missing database package installation in retirement/package_docker.py
- [x] All package_docker.py scripts now properly configured

#### 4.3 Final checks ✅ COMPLETE
- [x] Read and review the contents of the backend subdirectories: planner, reporter, retirement, tagger, charter
- [x] Check that they are consistent and simple:
  - Check that agent.py and lambda_handler.py are separate for all 5 agents
  - IMPORTANT: Check consistent and correct use of environment variables, correctly for Bedrock model and database access and Regions
  - IMPORTANT: the database packages need to be imported properly by all agents so that tests work properly locally and on lambda
  - Check everything will work locally (dotenv) and also when deployed remotely
  - Check consistent logging in all - just the right amount for important events, with consistent identification of the Agent doing the logging
  - Check tenacity is used consistently to retry rate limit errors with LLMs in a simple, reasonable way, with logging
  - Check any redundant code is removed; ensure methods are clean and simple; manage exceptions but don't go overboard
  - Check that methods / functions are short, clean, with docstrings but not overly commented otherwise
  - Check that the approach with RunContextWrapper is clean, correct, and used consistently for all agents that need it (use tools that need job id)
  - Check that each agent directory has a test_simple.py for local testing, and a test_full.py for testing after lambda deployment, and NO OTHER spurious testing
  - Check that the backend parent directory also has a test_simple.py for local testing and a test_full.py
- [x] Check package_docker.py scripts are consistent in style, simple, clear, package for Lambda boxes, use uv, and include all necessary files
- [x] Re-run test_simple tests for each agent individually to ensure no regression. Carefully look at every log message and ensure everything runs error free - do NOT assume that an error is "expected" - you've done this before and received a formal performance warning
- [x] Check the test_simple.py test in the backend folder for correctness, then run it

IMPORTANT: you MUST remember to use "uv run my_module.py" not "python my_module.py", within the directory of each agent.

#### 4.4 Package Lambda Functions ✅ COMPLETE
- [x] Package each agent with Docker (for correct architecture):
  - `cd backend/tagger && uv run package_docker.py`
  - `cd backend/reporter && uv run package_docker.py`
  - `cd backend/charter && uv run package_docker.py`
  - `cd backend/retirement && uv run package_docker.py`
  - `cd backend/planner && uv run package_docker.py`
- [x] Verify all zip files created (~50-100MB each)
- [x] Create a package_docker.py in the backend parent directory that runs each of these scripts
- [x] Test this package_docker.py

### Phase 5: Terraform Infrastructure ✅ COMPLETE

#### 5.1 Update Terraform Configuration ✅ COMPLETE
- [x] Review terraform/6_agents/main.tf
- [x] Ensure all Lambda functions have correct:
  - Memory (1024MB for agents, 2048MB for planner)
  - Timeout (60s for agents, 300s for planner)
  - Environment variables:
    - BEDROCK_MODEL_ID (without us. prefix)
    - BEDROCK_REGION (e.g., us-west-2)
    - DATABASE_CLUSTER_ARN
    - DATABASE_SECRET_ARN
    - DATABASE_NAME
    - DEFAULT_AWS_REGION
    - SAGEMAKER_ENDPOINT (planner and reporter)
  - IAM permissions (Bedrock, Database, Lambda invoke, SageMaker)
- [x] Add SQS queue with DLQ
- [x] Add EventBridge rule for SQS trigger
- [x] Updated to use S3 for Lambda deployment (packages >50MB)

#### 5.2 Deploy Infrastructure ✅ COMPLETE
- [x] Run: `cd terraform/6_agents && terraform init`
- [x] Run: `terraform plan` and review
- [x] Run: `terraform apply`
- [x] Verify all resources created successfully
- [x] Imported existing resources (IAM role, CloudWatch logs, SQS trigger)

#### 5.3 Deploy Lambda Functions ✅ COMPLETE
- [x] Lambda packages deployed via S3 during Terraform apply
- [x] All 5 Lambda functions created with correct code:
  - alex-planner (orchestrator)
  - alex-tagger
  - alex-reporter
  - alex-charter
  - alex-retirement
- [x] S3 bucket created: alex-lambda-packages-{account_id}
- [x] All packages uploaded to S3 automatically
- [x] Lambda functions reference S3 packages
- [x] Verified all 5 Lambda functions exist with correct configurations
- [x] CloudWatch log groups created for all functions

### Phase 6: Integration Testing

#### 6.1 Major issue with charter - review and remediation plan ✅ COMPLETE
- [x] Read the code in charter/agent.py
  - Reviewed code like: `create_chart.charts = {}` in create_agent - stateful anti-pattern
  - Reviewed the tool method create_chart signature - unreliable JSON string parameter
  - Reviewed the body of create_chart - poor implementation with function state
- [x] Write a new file guides/remediation.md that summarizes your self-review, and proposes a solution that is clean, reliable and simple
- [x] Write a detailed, clear action plan in remediation.md to fix this. Include logging in the fix so that the tool use can be tracked
- [x] IMPLEMENTED FIX: Replaced JSON string with structured parameters (list[str], list[float]), removed stateful functions, added proper validation

#### 6.2 SQS Integration Test ✅ COMPLETE
- [x] Prerequisites: Terraform must be applied (Phase 5 complete)
- [x] Run test via SQS (test_sqs_direct.py created and tested)
- [x] This successfully:
  - Created test job for 'test_user_001' in database
  - Sent job_id to SQS queue (alex-analysis-jobs)
  - Triggered Lambda via SQS event
  - Polled for completion (completed in 103 seconds)
  - Displayed formatted results
- [x] Verified all agents were invoked and results stored
- [x] Verified:
  - Report generates correctly (9291 chars)
  - Charts data is valid JSON (5 charts created)
  - Retirement projections calculate successfully
  - Job completes successfully with Charter working perfectly

#### 6.3 🔴 REGRESSION: Showstopper Issue with Charter Not Generating Charts

##### Critical Regression Detected
- **SEVERITY**: SHOWSTOPPER - Charter was working, now completely broken
- **SYMPTOM**: Charter agent runs successfully but creates 0 charts
- **IMPACT**: No visualizations = System unusable for production
- **STATUS**: UNRESOLVED - but strong evidence that this was caused by lambda timeout

##### SOLUTION

This is believed to be due to a Lambda Timeout causing the charter to fail.

ACTION PLAN FOR YOU (Claude Code)

- [X] Update timeout to be 5 mins for each agent, except the planner which should be 15 mins (it should already be)
- [X] Test each agent 3 times locally with test_simple.py in each directory. Monitor all log messages. If any issues, STOP and report to user (Ed)
- [X] Test run_simple.py in the backend directory 3 times. Monitor all log messages. If any issues, STOP and report to user (Ed)
- [X] Deploy using backend/deploy_all_lambdas.py
- [X] Check that new versions were deployed and uploaded to lambda properly - verify all, and verify timeouts
- [ ] Now test each agent 3 times remotely with test_full.py in each directory. Monitor all log messages. If any issues, STOP and report to user (Ed). FAIL - STOPPED - CHARTER STILL FAILING!
- [ ] Test run_full.py in the backend directory 3 times. Monitor all log messages. If any issues, STOP and report to user (Ed)

To watch for:

1. Note that since these can take several minutes to run, you may need to monitor for 3-5 minutes for completion
2. We believe that timeouts have been causing the issue, but it's not conclusively proven
3. There is also another point of suspicion: the charter agent uses a hacky approach to update charts in the database. (Charts accumulate in agent context, and get over-written each time. This might not work well with async / concurrent tool use.) Let's not fix this unless we prove it's a problem, but watch out for it. If necessary, this could be addressed by doing a database read, add chart, write. But we should only do this if we conclusively prove that this is a problem.

#### 6.4 Tagger Workflow Test
- [ ] Test with portfolio containing unknown instruments (e.g., new ETF) with unpopulated instrument in database
  - Verify tagger is called automatically
  - Verify allocations are populated in database
  - Verify price is populated in database
  - Verify main agents receive updated data
- [ ] Do not be dismissive of any error - if any problems, stop, explain to me (the user, Ed) and let's decide how to continue

#### 6.5 Multiple Accounts Test
- [ ] Do a code review to make sure all code can handle 1 user with multiple accounts
- [ ] Create a new test in backend called test_multiple_accounts.py
- [ ] Make this test create 1 user in the database with 3 accounts, each different portfolios
- [ ] Do a full run via SQS for this user
- [ ] Review the results and ensure everything works well - do not dismiss errors
- [ ] Do not be dismissive of any error - if any problems, stop, explain to me (the user, Ed) and let's decide how to continue
- [ ] The test should clean up db data after running, after clearly reporting what data was produced

#### 6.6 Larger Test
- [ ] Create a new test in backend called test_scale.py
- [ ] Set up 5 users in the database with portfolio sizes ranging from 0 to 10 positions
- [ ] Have 3 of the users having multiple accounts with different positions
- [ ] test_scale to run the analysis for all 5 users concurrently
- [ ] Review the results and ensure everything works well - do not dismiss errors
- [ ] Do not be dismissive of any error - if any problems, stop, explain to me (the user, Ed) and let's decide how to continue
- [ ] The test should clean up db data after running, after clearly reporting what data was produced


### Phase 7: Documentation & Cleanup

#### 7.1 Update Guide
- [ ] Update guides/6_agents.md with new architecture
- [ ] Add troubleshooting section
- [ ] Include example outputs

#### 7.2 Code Cleanup
- [ ] Remove debugging code
- [ ] Remove test stubs from main code
- [ ] Ensure all print statements use logger
- [ ] Verify no hardcoded values

#### 7.3 Final Validation
- [ ] Fresh clone of repository
- [ ] Follow student guide from scratch
- [ ] Confirm everything works as documented

## Testing Commands Reference

```bash
# Individual agent tests (local)
cd backend/reporter && uv run test_reporter.py
cd backend/charter && uv run test_charter.py
cd backend/retirement && uv run test_retirement.py

# Planner test (local with mocked agents)
cd backend/planner && uv run test_local.py

# Package Lambdas for deployment
cd backend/reporter && uv run package_docker.py
cd backend/charter && uv run package_docker.py
cd backend/retirement && uv run package_docker.py
cd backend/planner && uv run package_docker.py

# Integration test (with real Lambdas via SQS)
cd backend/planner && uv run test_integration.py

# Check job status
cd backend/planner && uv run check_jobs.py

# Terraform commands
cd terraform/6_agents
terraform init
terraform plan
terraform apply
terraform destroy
```

## Success Criteria

1. **No conflicts** - Agents run without tools/structured output errors
2. **Local testing works** - Can validate complete flow without AWS
3. **Planner autonomy** - Makes intelligent decisions about which agents to call
4. **Clean results** - Database contains well-structured analysis data
5. **Student friendly** - Code is clear, tests are simple, errors are informative

## Notes

- Keep code concise - no unnecessary try/catch blocks
- Use environment variables for configuration
- Let the database be the source of truth
- Focus on demonstrating agent collaboration patterns
- Make the output impressive but not overly complex