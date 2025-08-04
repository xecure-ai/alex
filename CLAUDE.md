# Project: Alex

## Overall context
- This is a project being developed as part of Ed's course "AI in Production"
- Ed is writing this code which thousands of students will clone; they will then follow the steps to deploy
- Students may be on Windows PC, Mac or Linux; the instructions needs to work on all systems
- This project is called Alex - the Agentic Lifetime Equities Explainer - it's an Agentic AI Platform to be your personal financial planner for your portfolios
- The project root is ~/projects/alex
- There is a .env file in the project root; you may not be able to see it for security reasons, but it's there, with OPENAI_API_KEY

## Project organization
backend
- There will be separate projects within this folder for each of the backend deployments
- Each one will have its own uv project
frontend
- A NextJS typescript app will be built eventually
terraform
- Here will be the terraform scripts for the deployment

## OpenSearch + Lambda Architecture Decisions (August 2025)

### Architecture Approach
Based on research and lessons learned from SageMaker deployment:
1. **OpenSearch Serverless** - Fully managed, auto-scaling vector database
2. **Lambda with inline dependencies** - Simple zip deployment, no layers
3. **API Gateway HTTP API** - Simpler and cheaper than REST API
4. **API Key authentication** - Protect endpoints from public access

### Implementation Decisions
1. **Zip Creation**: Python script for cross-platform compatibility (Windows/Mac/Linux)
2. **Authentication**: API Gateway API keys to prevent unauthorized access and protect SageMaker costs
3. **Terraform Structure**: Separate modules for clarity:
   - `modules/opensearch/` - OpenSearch Serverless resources
   - `modules/lambda/` - Lambda function and IAM
   - `modules/api_gateway/` - API Gateway and authentication
   
### Key Principles
- Start simple, mainstream solutions only
- Cross-platform compatibility is mandatory
- Security by default (API keys from start)
- Modular but not complex
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
6. **Pay attention to dates** - if Ed says it's 2025, use 2025 resources

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

2. ✅ **OpenSearch + Lambda Ingest Pipeline** (Guide 3)
   - OpenSearch Serverless vector database
   - Lambda function with packaged dependencies
   - API Gateway with API key authentication
   - Management scripts for testing and maintenance

3. ✅ **Researcher Agent Service** (Guide 4)
   - AWS App Runner deployment
   - OpenAI Agents SDK with gpt-4.1-mini
   - Docker with cross-platform build (`--platform linux/amd64`)
   - Automated research generation and storage

4. ✅ **Complete Guide Documentation** (Guides 1-4)
   - Cross-platform instructions (Mac/Windows/Linux)
   - Architecture diagrams (Mermaid format)
   - Troubleshooting sections
   - All tested end-to-end

### Architecture Overview
```
backend/
├── ingest/          # Lambda function (uv project)
│   ├── ingest.py    # Main Lambda handler
│   ├── package.py   # Cross-platform packaging script
│   ├── test_api.py  # Ingest testing
│   ├── search_api.py # Search testing
│   └── cleanup_api.py # Database management
└── researcher/      # App Runner service (uv project)
    ├── server.py    # FastAPI + OpenAI Agents
    ├── deploy.py    # Cross-platform deployment
    └── test_research.py # Service testing

terraform/
├── main.tf          # Root configuration
├── variables.tf     # Required: aws_account_id, openai_api_key
└── modules/         # Modular infrastructure
    ├── opensearch/  # Vector database
    ├── lambda/      # Ingest function
    ├── api_gateway/ # REST API
    └── app_runner/  # Researcher service

guides/
├── 1_permissions.md    # IAM setup
├── 2_sagemaker.md     # Embedding model
├── 3_opensearch_lambda.md # Ingest pipeline
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
  - `OPENSEARCH_ENDPOINT` - Updated after infrastructure changes
  - `ALEX_API_KEY` - For API Gateway authentication
  - `AWS_ACCOUNT_ID` - Set via AWS CLI during deployment

#### Infrastructure Patterns
- Everything deployed via Terraform with variables
- OpenSearch endpoint changes only after `terraform destroy`
- API Gateway uses REST API (not HTTP API) for API key support
- App Runner for containers, Lambda for simple functions

#### Common Gotchas
1. **OpenSearch endpoint stale in .env** - Update after terraform destroy/apply
2. **Docker architecture on Apple Silicon** - Always use `--platform linux/amd64`
3. **Lambda packaging** - Use package.py for cross-platform compatibility
4. **SageMaker embeddings** - Returns [[[embedding]]], needs unpacking
5. **OpenSearch consistency** - 5-10 second delay after ingestion

### Next Steps (Not Started)
- Frontend development (NextJS with TypeScript)
- Additional agent capabilities
- Portfolio analysis features
- User authentication and multi-tenancy