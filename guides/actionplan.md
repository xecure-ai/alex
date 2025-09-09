# Action Plan - Part 6 Agent Orchestra Fix

## Current Status (Last Updated: 2025-09-08)

**Phase 3**: ✅ COMPLETE - All orchestrator fixes done  
**Phase 4**: 🔧 IN PROGRESS - Package scripts fixed, packaging blocked by network  
**Phase 5**: ⏳ TODO - Terraform infrastructure deployment  
**Phase 6**: ⏳ TODO - Integration testing  
**Phase 7**: ⏳ TODO - Documentation & cleanup  

### Next Steps When Network Available:
1. Complete Phase 4.3: Run the 5 packaging commands to create Lambda deployment zips
2. Complete Phase 5.1-5.2: Deploy Terraform infrastructure to create Lambda functions
3. Complete Phase 5.3: Deploy Lambda function code using deploy_all_lambdas.py
4. Complete Phase 6: Run integration tests to verify everything works

## Problem Statement

The OpenAI Agents SDK (formerly Swarm) currently doesn't support using both tools AND structured outputs simultaneously in a single agent. When we configure an agent with both:
- `tools=[...]` for calling functions
- `output_type=SomeModel` for structured outputs

The agent fails with errors, making our orchestrator pattern unusable in its current form.

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

### Important: AWS Region Handling for Multi-Region Services

**Problem Discovered**: When using services in different AWS regions (e.g., Bedrock in us-west-2, Aurora in us-east-1), changing the `AWS_REGION` environment variable affects ALL AWS SDK calls, causing connection failures.

**Solution**: The database client now extracts the region directly from the Aurora cluster ARN, ensuring it always connects to the correct region regardless of environment variable changes. This pattern should be followed for any service that needs a specific region.

**Key Lessons**:
1. Never assume changing `AWS_REGION` only affects one service
2. Services should derive their region from their configuration (ARNs) when possible
3. Avoid manipulating and restoring environment variables as a workaround
4. Test multi-region scenarios thoroughly

The InstrumentTagger (special case):
- Called directly via Lambda invocation (not as an agent tool)
- Runs as a pre-processing step before the main orchestration
- Already implemented correctly in `handle_missing_instruments()`
- Updates the database with missing instrument allocations

Each specialized agent (Reporter, Charter, Retirement) will:
- Use **tools only** to generate and store their analysis
- Have an `update_job_results` tool to write directly to the database
- Generate analysis through natural language processing (no structured output models)
- Return simple success confirmations to the orchestrator

The orchestrator (Planner) will:
- Pre-process with InstrumentTagger (non-autonomous, always runs if needed)
- Use **tools only** to call other agents and finalize results
- Have autonomy to decide which agents to invoke (Reporter, Charter, Retirement)
- Pass job_id to each agent for database access
- Use a `finalize_job` tool to mark analysis complete

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

#### 4.3 Final review, cleanup and minor refactor for agent consistency
- [ ] Read and review the contents of the backend subdirectories: planner, reporter, retirement, tagger, charter
- [ ] Make minor refinements to make them consistent and simple:
  - Ensure agent.py and lambda_handler.py are separate for all 5 agents
  - Ensure consistent use of environment variables, separately for Bedrock model and database access
  - Ensure everything will work locally (dotenv) and also when deployed remotely
  - Ensure consistent logging in all - just the right amount for important events, with consistent identification of the Agent doing the logging
  - Ensure tenacity is used consistently to retry rate limit errors with LLMs in a simple, reasonable way, with logging
  - Ensure any redundant code is removed; ensure methods are clean and simple; manage exceptions but don't go overboard
- [ ] Update package_docker.py scripts as needed to ensure all are consistent in style, simple, clear, package for Lambda boxes, use uv, and include all necessary files
- [ ] Re-run local tests for each agent to ensure no regression. Carefully look at every log message and ensure everything runs error free

#### 4.4 Package Lambda Functions
- [ ] Package each agent with Docker (for correct architecture):
  - `cd backend/tagger && uv run package_docker.py`
  - `cd backend/reporter && uv run package_docker.py`
  - `cd backend/charter && uv run package_docker.py`
  - `cd backend/retirement && uv run package_docker.py`
  - `cd backend/planner && uv run package_docker.py`
- [ ] Verify all zip files created (~50-100MB each)

### Phase 5: Terraform Infrastructure

#### 5.1 Update Terraform Configuration
- [ ] Review terraform/6_agents/main.tf
- [ ] Ensure all Lambda functions have correct:
  - Memory (1024MB for agents, 2048MB for planner)
  - Timeout (60s for agents, 300s for planner)
  - Environment variables:
    - BEDROCK_MODEL_ID (without us. prefix)
    - BEDROCK_REGION (e.g., us-west-2)
    - DATABASE_CLUSTER_ARN
    - DATABASE_SECRET_ARN
    - DATABASE_NAME
  - IAM permissions (Bedrock, Database, Lambda invoke)
- [ ] Add SQS queue with DLQ
- [ ] Add EventBridge rule for SQS trigger
- [ ] Note: tenacity package must be included in Lambda layers

#### 5.2 Deploy Infrastructure
- [ ] Run: `cd terraform/6_agents && terraform init`
- [ ] Run: `terraform plan` and review
- [ ] Run: `terraform apply`
- [ ] Verify all resources created successfully

#### 5.3 Deploy Lambda Functions
- [ ] Review and update deploy_all_lambdas.py script:
  - Check it references correct Lambda function names
  - Verify it looks for correct zip file names
  - Ensure it handles all 5 agents (tagger, reporter, charter, retirement, planner)
  - Update any outdated boto3 calls or Python patterns
- [ ] Deploy all Lambda functions:
  - `cd backend && uv run deploy_all_lambdas.py`
- [ ] This script will:
  - Create S3 bucket if needed (alex-lambda-packages-{account_id})
  - Upload all packages to S3
  - Update Lambda function code from the zip files
- [ ] Verify all 5 Lambda functions updated in AWS Console
- [ ] Check CloudWatch logs for any deployment errors

### Phase 6: Integration Testing

#### 6.1 SQS Integration Test
- [ ] Prerequisites: Terraform must be applied (Phase 5 complete)
- [ ] Run test_integration.py:
  - `cd backend/planner && uv run test_integration.py`
- [ ] This will:
  - Create test job for 'test_user' in database
  - Send job_id to SQS queue (created by Terraform)
  - Trigger Lambda via SQS event
  - Poll for completion (3 minute timeout)
  - Display formatted results
- [ ] Verify all agents were invoked and results stored
- [ ] Verify:
  - Report generates correctly
  - Charts data is valid JSON
  - Retirement projections calculate
  - Job completes successfully

#### 6.2 Full End-to-End Tests
- [ ] Run additional test scenarios to verify agent autonomy

#### 6.3 Autonomy Test
- [ ] Test with simple portfolio (1 position)
  - Verify planner skips charter
- [ ] Test with complex portfolio (10+ positions)
  - Verify planner calls all agents
- [ ] Test with no retirement goals
  - Verify planner skips retirement agent

#### 6.4 Tagger Workflow Test
- [ ] Test with portfolio containing unknown instruments (e.g., new ETF)
  - Verify tagger is called automatically
  - Verify allocations are populated in database
  - Verify main agents receive updated data
- [ ] Test with all known instruments
  - Verify tagger is NOT called (efficiency)
- [ ] Test tagger failure handling
  - Verify orchestration continues even if tagger fails

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