# Action Plan - Part 6 Agent Orchestra Fix

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

#### 2.3 Retirement Agent
- [ ] Remove RetirementAnalysis structured output model
- [ ] Add `update_job_retirement` tool to write to retirement_payload field
- [ ] Add `run_monte_carlo` tool for simulations
- [ ] Modify lambda_handler to:
  - Accept job_id in event
  - Load portfolio from database
  - Run agent with tools to generate and store projections
  - Return simple success response
- [ ] Create test_retirement.py with minimal test case
- [ ] Test locally with: `uv run test_retirement.py`

### Phase 3: Fix Orchestrator (Planner)

#### 3.1 Remove Structured Output
- [ ] Remove AnalysisResult model completely
- [ ] Update templates.py with clearer autonomy instructions
- [ ] Keep agent configuration to tools only

#### 3.2 Simplify Tool Functions
- [ ] Update `invoke_reporter` to pass job_id only
- [ ] Update `invoke_charter` to pass job_id only  
- [ ] Update `invoke_retirement` to pass job_id only
- [ ] Remove hardcoded return values
- [ ] Add `finalize_job` tool for completion

#### 3.3 Add Local Testing Support
- [ ] Add MOCK_LAMBDAS environment variable check
- [ ] Implement local agent calling when MOCK_LAMBDAS=true
- [ ] Create test_planner_local.py for isolated testing

### Phase 4: Integration Testing

#### 4.1 Local Integration Test
- [ ] Create test_integration_local.py that:
  - Creates a test job with sample portfolio
  - Runs planner with MOCK_LAMBDAS=true
  - Verifies all agents stored their results
  - Checks job marked as completed
- [ ] Run: `uv run test_integration_local.py`

#### 4.2 Lambda Deployment Test
- [ ] Package all agents with docker: `uv run package_docker.py`
- [ ] Deploy to Lambda functions
- [ ] Create test_integration_lambda.py that:
  - Sends job to SQS queue
  - Monitors job status
  - Retrieves and displays results
- [ ] Run: `uv run test_integration_lambda.py`

### Phase 5: Terraform & Infrastructure

#### 5.1 Update Terraform Configuration
- [ ] Review terraform/6_agents/main.tf
- [ ] Ensure all Lambda functions have correct:
  - Memory (1024MB for agents, 2048MB for planner)
  - Timeout (60s for agents, 300s for planner)
  - Environment variables (BEDROCK_MODEL_ID, etc.)
  - IAM permissions (Bedrock, Database, Lambda invoke)
- [ ] Add SQS queue with DLQ
- [ ] Add EventBridge rule for SQS trigger

#### 5.2 Deploy Infrastructure
- [ ] Run: `cd terraform/6_agents && terraform init`
- [ ] Run: `terraform plan` and review
- [ ] Run: `terraform apply`
- [ ] Verify all resources created successfully

### Phase 6: End-to-End Testing

#### 6.1 Full System Test
- [ ] Create run_full_test.py that:
  - Creates realistic test portfolio
  - Submits to SQS
  - Polls for completion
  - Displays formatted results
- [ ] Run: `uv run run_full_test.py`
- [ ] Verify:
  - Report generates correctly
  - Charts data is valid JSON
  - Retirement projections calculate
  - Job completes successfully

#### 6.2 Autonomy Test
- [ ] Test with simple portfolio (1 position)
  - Verify planner skips charter
- [ ] Test with complex portfolio (10+ positions)
  - Verify planner calls all agents
- [ ] Test with no retirement goals
  - Verify planner skips retirement agent

#### 6.3 Tagger Workflow Test
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
cd backend/planner && uv run test_planner_local.py

# Integration test (local)
cd backend/planner && uv run test_integration_local.py

# Deploy all Lambdas
cd backend && uv run deploy_all_lambdas.py

# Full system test (with real Lambdas)
cd backend/planner && uv run run_full_test.py

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