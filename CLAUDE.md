# Project "Alex"
- This is part of Ed's course "AI in Production"
- Students may be on Windows PC, Mac or Linux; the instructions needs to work on all systems
- This project is called Alex - the Agentic Lifetime Equities Explainer - it's an Agentic AI Platform to be your personal financial planner for your portfolios, deployed on AWS
- The project root is ~/projects/alex
- There is a .env file in the project root; you may not be able to see it for security reasons, but it's there, with OPENAI_API_KEY
- The guides folder contains instructions for each step of the project. These guides are for students, NOT for Ed (the user). For example: if we need to add a Python package, Ed needs to run `uv add package_name`. The students will NOT need to do this, because it will be in pyproject.toml, and in the repo.
- The students might be in any AWS region. BE VERY THOUGHTFUL about this. Some infrastructure must be in us-east-1, but mostly it must be in the student's region.
- ALWAYS be as simple as possible. Always be idiomatic - use simple, popular, common, up-to-date approaches.
- Approach in small steps that can be tested carefully.

## Project organization
backend
- There will be separate projects within this folder for each of the backend deployments
- Each one will have its own uv project
frontend
- A NextJS typescript app will be built eventually
terraform
- Here will be the terraform scripts for the deployment

## S3 Vectors Architecture (Migrated from OpenSearch - August 2025)

### Architecture Approach
Using S3 Vectors for 90% cost savings (previously used OpenSearch - this has been replaced and there should be no mention of it in the guides)
1. **S3 Vectors** - AWS native vector storage service, serverless
2. **Lambda with inline dependencies** - Simple zip deployment, no layers
3. **API Gateway REST API** - Required for API key authentication
4. **API Key authentication** - Protect endpoints from public access

### Implementation Decisions
1. **Zip Creation**: Python script for cross-platform compatibility (Windows/Mac/Linux)
2. **Authentication**: API Gateway API keys to prevent unauthorized access
3. **Terraform Structure**: Separate modules for clarity:
   - `modules/s3_vectors/` - S3 Vectors bucket and resources
   - `modules/lambda_s3vectors/` - Lambda function and IAM
   - `modules/api_gateway/` - REST API with API key auth
   
### Key Principles
- S3 Vectors is 90% cheaper than OpenSearch
- IAM permissions require `s3vectors:*` with `Resource: "*"`
- Cross-platform compatibility is mandatory
- Security by default (API keys from start)
- Everything in Terraform for single deployment

## Important Learning: SageMaker Deployment Post-Mortem (August 2025)

### What Happened
We spent 2+ hours implementing a complex custom model packaging approach for deploying all-MiniLM-L6-v2 on SageMaker, involving:
- Custom inference.py scripts
- Model packaging into tar.gz files
- S3 bucket creation and management
- Python/uv project for testing
- Multiple iterations with outdated containers (2023 PyTorch containers in 2025)

### What Went Wrong
1. **Jumped to complexity** - Assumed we needed custom scripts without researching simpler options
2. **Used outdated approaches** - Implemented 2023 patterns when 2025 best practice is much simpler
3. **Ignored context** - Despite being told it's August 2025, searched for 2024 info and used old containers
4. **Didn't validate approach** - Built everything before confirming it was the right way

### The Right Approach (Discovered After 2 Hours)
- Use HuggingFace containers with `HF_MODEL_ID` environment variable
- No model packaging needed - it downloads automatically
- No S3 buckets, no Python code, no custom scripts
- Just Terraform and done

### Going Forward - ALWAYS:
1. **Research current best practices FIRST** - especially check the year
2. **Start with the simplest possible approach** 
3. **Challenge every piece of complexity** - ask "is this necessary?"
4. **Validate the approach before building** - quick proof of concept
5. **Check if this is how everyone else does it** - mainstream solutions for teaching
6. **Pay attention to dates** - use 2025 resources

### Key Lesson
For well-supported models like sentence-transformers, the cloud providers have already solved the deployment problem. Look for their simple solution before building a complex one.

## Important Learning: App Runner Docker Deployment Post-Mortem (August 2025)

### What Happened
Spent 30+ minutes troubleshooting App Runner deployment failure (exit code 255) with increasingly complex theories before identifying a simple, common architecture mismatch issue.

### What Went Wrong
1. **Jumped to unlikely theories** - Suggested timeouts, package manager issues, path problems
2. **Overcomplicated solutions** - Tried removing uv, simplifying Docker, changing configurations
3. **Ignored obvious clues** - M1 Mac + Docker + exit code 255 is a classic architecture mismatch pattern
4. **Didn't search properly** - Should have immediately searched "M1 Docker App Runner exit code 255"
5. **No common sense filtering** - Each theory was increasingly unlikely; didn't step back to think

### The Right Approach (User Identified Immediately)
- M1 Macs build ARM images by default
- App Runner expects x86_64/amd64 architecture
- Solution: Add `--platform linux/amd64` to Docker build
- This is one of the most common Docker deployment issues for M1 users

### Problem Solving Principles - ALWAYS:
1. **Apply common sense first** - Is this theory likely? Is it simple?
2. **Look for simple explanations** - Most problems have simple causes
3. **Identify the problem before guessing solutions** - Understand what's happening first
4. **Search for exact error patterns** - "M1 Mac Docker exit code 255" would have found it instantly
5. **Consider common issues first** - Architecture mismatches are extremely common with M1 Macs
6. **When stuck, step back** - If solutions seem increasingly complex, you're probably on the wrong track

### Key Lesson
When deployment works locally but fails remotely, especially with generic exit codes, check the basics first: architecture, environment variables, ports. Don't invent complex theories when simple, common issues are far more likely.

## Current Status

### Completed
1. ✅ **SageMaker Serverless endpoint** (Guide 2)
   - Model: all-MiniLM-L6-v2 
   - Serverless configuration for cost efficiency
   - HuggingFace container with HF_MODEL_ID environment variable

2. ✅ **S3 Vectors + Lambda Ingest Pipeline** (Guide 3)
   - S3 Vectors for vector storage (90% cheaper than OpenSearch)
   - Lambda function with packaged dependencies
   - API Gateway REST API with API key authentication
   - Test scripts: test_api.py, test_search_s3vectors.py, cleanup_s3vectors.py

3. ✅ **Researcher Agent Service** (Guide 4)
   - AWS App Runner deployment with bulletproof deployment process
   - OpenAI Agents SDK with gpt-4.1-mini
   - Playwright MCP Server for web browsing
   - Docker with cross-platform build (`--platform linux/amd64`)
   - Automated research generation and storage to S3 Vectors
   - Fixed environment variable loading with `load_dotenv(override=True)`

4. ✅ **Complete Guide Documentation** (Guides 1-4)
   - Cross-platform instructions (Mac/Windows/Linux)
   - Architecture diagrams (Mermaid format)
   - Troubleshooting sections
   - All tested end-to-end

### Architecture Overview
```
backend/
├── ingest/          # Lambda function (uv project)
│   ├── ingest.py    # Main Lambda handler for S3 Vectors
│   ├── package.py   # Cross-platform packaging script
│   ├── test_api.py  # Ingest testing
│   ├── test_search_s3vectors.py # S3 Vectors search testing
│   └── cleanup_s3vectors.py # S3 Vectors cleanup (batch of 30)
└── researcher/      # App Runner service (uv project)
    ├── server.py    # FastAPI + OpenAI Agents
    ├── deploy.py    # Deployment with unique tags + env vars
    ├── test_research.py # Service testing
    ├── mcp_servers.py # Playwright browser config
    └── tools.py     # Ingest tool with retry logic

terraform/
├── main.tf          # Root configuration
├── variables.tf     # Required: aws_account_id, openai_api_key
└── modules/         # Modular infrastructure
    ├── s3_vectors/  # S3 Vectors bucket
    ├── lambda_s3vectors/ # Lambda for S3 Vectors
    ├── api_gateway/ # REST API with API keys
    └── app_runner/  # Researcher service

guides/
├── 1_permissions.md    # IAM setup
├── 2_sagemaker.md     # Embedding model
├── 3_ingest.md       # S3 Vectors ingest pipeline
├── 4_researcher.md    # AI agent service
└── architecture.md    # System overview
```

### Key Technical Decisions

#### Python Package Management
- **ALWAYS use `uv`** for all Python commands
- Each backend service has its own uv project
- Commands: `uv run script.py`, `uv add package`, never plain `python`
- Cross-platform compatibility is mandatory

#### Environment Variables
- `.env` file in project root contains all configuration
- Loaded with `python-dotenv` using `load_dotenv(override=True)`
- Key variables:
  - `OPENAI_API_KEY` - For researcher agent
  - `ALEX_API_ENDPOINT` - API Gateway endpoint for ingest
  - `ALEX_API_KEY` - For API Gateway authentication
  - `AWS_ACCOUNT_ID` - Set via AWS CLI during deployment
  - `SAGEMAKER_ENDPOINT` - Embedding model endpoint

#### Infrastructure Patterns
- Everything deployed via Terraform with variables
- S3 Vectors bucket name includes account ID for uniqueness
- API Gateway uses REST API (not HTTP API) for API key support
- App Runner for containers, Lambda for simple functions
- App Runner deployment uses UPDATE_SERVICE with unique tags (not START_DEPLOYMENT)

#### Common Gotchas
1. **S3 Vectors permissions** - Must use `Resource: "*"` (not scoped ARNs)
2. **Docker architecture on Apple Silicon** - Always use `--platform linux/amd64`
3. **Lambda packaging** - Use package.py for cross-platform compatibility
4. **SageMaker embeddings** - Returns [[[embedding]]], needs unpacking
5. **S3 Vectors consistency** - Updates are immediate (no delay)
6. **App Runner caching** - Use unique tags + UPDATE_SERVICE to force new deployments
7. **Browser in containers** - Check for AWS_EXECUTION_ENV, not just /.dockerenv
8. **S3 Vectors topK limit** - Maximum 30 results per query

### Recent Session Learnings (August 2025)

#### App Runner Browser Issues & Fix
1. **Problem**: Browser wasn't working in App Runner ("browser is missing the required Chrome installation")
2. **Root Cause**: Container detection was checking for `/.dockerenv` which doesn't exist in App Runner's ECS Fargate
3. **Solution**: Check for `AWS_EXECUTION_ENV` environment variable as well
4. **Key Learning**: App Runner runs in ECS Fargate, not as PID 1, so container detection must be broader

#### App Runner Deployment Caching Issue & Fix
1. **Problem**: App Runner wasn't using updated Docker images despite deployments
2. **Root Cause**: Using `latest` tag with START_DEPLOYMENT doesn't force image pulls
3. **Solution**: 
   - Use unique timestamp tags (e.g., `deploy-1754519257`)
   - Use `update-service` operation instead of `start-deployment`
   - Modified deploy.py to implement this pattern
4. **Key Learning**: App Runner can cache images aggressively; unique tags ensure fresh deployments

#### Environment Variables for Vector Storage
1. **Problem**: Researcher couldn't store vectors ("Alex API not configured")
2. **Root Cause**: deploy.py wasn't loading .env file, so ALEX_API_KEY and ALEX_API_ENDPOINT were empty
3. **Solution**: Added `load_dotenv(override=True)` to deploy.py
4. **Key Learning**: Always ensure deployment scripts load environment variables

#### Current Known Issues
1. **Browser Timeouts**: Playwright MCP sometimes times out (60s) in App Runner
   - Increased timeout to 120s but may need further optimization
   - Could be that Browser is stuck on a modal or anti-scrape protection
2. **Retries**: Ingestion has retry logic for cold starts, browser operations don't

### Next Steps (Not Started)
- Frontend development (NextJS with TypeScript)
- Additional agent capabilities
- Portfolio analysis features
- User authentication and multi-tenancy
- Optimize browser performance in App Runner